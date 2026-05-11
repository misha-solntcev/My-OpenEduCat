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
        """СБРОС: Обработка любого количества записей"""
        res = super(OpSession, self).lecture_draft()
        # Ищем все связанные журналы одной пачкой
        sheets = self._get_linked_sheets()
        if sheets:
            # Массово переводим журналы в черновик
            sheets.action_attendance_draft()
        return res

    def lecture_confirm(self):
        """УТВЕРЖДЕНИЕ: Массовое создание шапок"""
        res = super(OpSession, self).lecture_confirm()
        # Для каждой сессии в наборе гарантируем наличие журнала
        for rec in self:
            self.env['op.attendance.sheet'].create_sheet_for_session(rec)
        return res

    def lecture_start(self):
        """СТАРТ: Массовая генерация списков детей"""
        # Сначала проталкиваем черновики и отмененные в confirm
        to_confirm = self.filtered(lambda r: r.state in ['draft', 'cancel'])
        if to_confirm:
            to_confirm.lecture_confirm()
            
        res = super(OpSession, self).lecture_start()
        
        # Запускаем журналы
        sheets = self._get_linked_sheets()
        for sheet in sheets:
            if sheet.state != 'start':
                sheet.action_attendance_start()
        return res

    def lecture_done(self):
        """ЗАВЕРШЕНИЕ: Массовое закрытие и расчет статистики"""
        # Все, что не в 'start', проталкиваем вперед по цепочке
        to_start = self.filtered(lambda r: r.state != 'start')
        if to_start:
            to_start.lecture_start()
            
        res = super(OpSession, self).lecture_done()
        
        # Закрываем журналы
        sheets = self._get_linked_sheets()
        for sheet in sheets:
            if sheet.state != 'done':
                sheet.action_attendance_done()
        return res

    def lecture_cancel(self):
        """ОТМЕНА: Массовая проверка и блокировка"""
        sheets = self._get_linked_sheets()
        # В Odoo 18 лучше вызвать метод для каждой записи, 
        # чтобы увидеть ошибку ValidationError для конкретного журнала
        for sheet in sheets:
            sheet.action_attendance_cancel()
        return super(OpSession, self).lecture_cancel()

    def lecture_edit(self):
        """РЕДАКТИРОВАНИЕ: Массовый возврат в работу"""
        res = super(OpSession, self).lecture_edit()
        sheets = self._get_linked_sheets()
        if sheets:
            sheets.action_attendance_edit()
        return res