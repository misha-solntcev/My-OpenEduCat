from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class OpSession(models.Model):
    _inherit = "op.session"

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---

    def _get_linked_sheets(self):
        """ОПТИМИЗАЦИЯ: Поиск журналов сразу для всего набора уроков (RecordSet)"""
        return self.env['op.attendance.sheet'].sudo().search([('session_id', 'in', self.ids)])

    def get_attendance(self):
        """Метод кнопки остается для ОДНОЙ записи (ensure_one)"""
        self.ensure_one()
        if self.state == 'cancel':
            raise ValidationError(_("Нельзя открыть журнал для отмененного урока."))
        
        # Ищем журнал только для текущей записи
        sheet = self.env['op.attendance.sheet'].sudo().search([('session_id', '=', self.id)], limit=1)
        
        if not sheet:
            if self.state == 'draft':
                raise ValidationError(_("Сначала утвердите урок."))
            sheet = self.env['op.attendance.sheet'].create_sheet_for_session(self)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'op.attendance.sheet',
            'view_mode': 'form',
            'res_id': sheet.id,
            'target': 'current',
        }

    # --- КАСКАДНАЯ ЛОГИКА (Массовая обработка) ---

    def lecture_draft(self):
        """СБРОС: Возврат в черновик расписания"""
        sheets = self._get_linked_sheets()
        if sheets:
            # Ищем ЛЮБЫЕ данные: оценки, статусы посещаемости или примечания
            data_exists = sheets.attendance_line.filtered(
                lambda l: l.grade_1 or l.grade_2 or l.grade_3 or l.attendance_type_id or l.remark
            )
            if data_exists:
                raise ValidationError(_(
                    "Нельзя вернуть урок в черновик! В журналах уже есть данные (оценки или отметки о посещаемости)."
                ))
            # Если данных нет — удаляем пустые оболочки журналов
            sheets.unlink()
        return super(OpSession, self).lecture_draft()

    def lecture_confirm(self):
        """УТВЕРЖДЕНИЕ: Создание журналов + сразу генерируем список учеников.

        Раньше строки создавались только на lecture_start, из-за чего
        утверждённый урок в миниаппе выглядел как «Ученики не найдены».
        """
        res = super(OpSession, self).lecture_confirm()
        for rec in self:
            sheet = self.env['op.attendance.sheet'].create_sheet_for_session(rec)
            sheet.action_generate_lines()
        return res

    def lecture_start(self):
        """СТАРТ: Перевод в рабочий режим + СИНХРОНИЗАЦИЯ списка.

        action_generate_lines() дополняет строки только если журнал пуст.
        Между утверждением и стартом состав мог измениться (новенький /
        выбывший) — досинхронизируем через _sync_lines().
        """
        res = super(OpSession, self).lecture_start()
        sheets = self._get_linked_sheets()
        if sheets:
            sheets.action_generate_lines()  # пустые журналы
            sheets._sync_lines()            # досоздать/убрать изменившихся
            sheets.write({'state': 'start'})
        return res

    def lecture_done(self):
        """ЗАВЕРШЕНИЕ: Закрытие и фиксация успеваемости"""
        res = super(OpSession, self).lecture_done()
        sheets = self._get_linked_sheets()
        if sheets:
            sheets.write({'state': 'done'})
            sheets._transfer_grades_to_stats() # Пересчет статистики
        return res

    def lecture_cancel(self):
        """ОТМЕНА: Блокировка при наличии данных"""
        sheets = self._get_linked_sheets()
        if sheets:
            # Проверяем все важные поля на заполненность
            data_exists = sheets.attendance_line.filtered(
                lambda l: l.grade_1 or l.grade_2 or l.grade_3 or l.attendance_type_id or l.remark
            )
            if data_exists:
                raise ValidationError(_(
                    "Отмена невозможна! В журнале уже отмечена посещаемость или выставлены оценки."
                ))
            sheets.write({'state': 'cancel'})
        return super(OpSession, self).lecture_cancel()

    def lecture_edit(self):
        """РЕДАКТИРОВАНИЕ: Возврат в Start"""
        res = super(OpSession, self).lecture_edit()
        sheets = self._get_linked_sheets()
        if sheets:
            sheets.write({'state': 'start'})
        return res

    # --- CRON: переводим уроки по расписанию (замена Base Automation 18/19) ---

    @api.model
    def _cron_advance_sessions(self):
        """confirm -> start при наступлении start_datetime,
        start -> done после end_datetime.

        Вызывается ir.cron каждые 5 минут. Тайминги совпадают со старыми
        рукотворными правилами 18/19: start = start_datetime + 0,
        done = end_datetime + 0. На confirm старый крон не вставал —
        утверждение остаётся ручным (или через мастер-расписание).

        Чтобы урок не ждал до 5 минут («тик через 1 минуту после начала
        урока — следующая проверка через 4»), переводим в start ЗАРАНЕЕ:
        как только до start_datetime осталось < 2 минут. Учитель открывает
        журнал по звонку, а не по таймеру.
        """
        now = fields.Datetime.now()
        soon = now + timedelta(minutes=5)

        to_start = self.sudo().search([
            ('state', '=', 'confirm'),
            ('start_datetime', '<=', soon),  # начнётся < чем через 5 мин
            ('end_datetime', '>', now),      # ещё не закончился
        ])
        if to_start:
            to_start.lecture_start()
            _logger.info("Session lifecycle: started %d session(s)", len(to_start))

        # start -> done: уроки, чьё время прошло (не раньше чем сутки назад,
        # чтобы не трогать исторические записи и не перепроводить
        # пропущенные обработкой)
        cutoff = now - timedelta(days=1)
        to_done = self.sudo().search([
            ('state', '=', 'start'),
            ('end_datetime', '<=', now),
            ('end_datetime', '>=', cutoff),
        ])
        if to_done:
            to_done.lecture_done()
            _logger.info("Session lifecycle: done %d sessions", len(to_done))