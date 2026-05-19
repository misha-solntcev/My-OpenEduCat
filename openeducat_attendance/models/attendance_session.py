from odoo import models, fields, api, _
from odoo.exceptions import ValidationError  

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
        """УТВЕРЖДЕНИЕ: Создание журналов"""
        res = super(OpSession, self).lecture_confirm()
        for rec in self:
            self.env['op.attendance.sheet'].create_sheet_for_session(rec)
        return res

    def lecture_start(self):
        """СТАРТ: Перевод в рабочий режим"""
        res = super(OpSession, self).lecture_start()
        sheets = self._get_linked_sheets()
        if sheets:
            sheets.action_generate_lines() # Генерируем список детей
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