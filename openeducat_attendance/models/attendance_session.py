from odoo import models, fields, api, _
from odoo.exceptions import ValidationError  

class OpSession(models.Model):
    _inherit = "op.session"

    def _get_linked_sheet(self):
        """Вспомогательный метод для поиска связанного журнала"""
        return self.env['op.attendance.sheet'].sudo().search([('session_id', '=', self.id)], limit=1)

    def get_attendance(self):
        """Метод для кнопки 'Attendance Sheet' (Stat-button)"""
        self.ensure_one()
        sheet = self._get_linked_sheet()
        if sheet:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'op.attendance.sheet',
                'view_mode': 'form',
                'res_id': sheet.id,
                'target': 'current',
            }
        else:
            raise ValidationError(_("Журнал для этого занятия еще не создан. Сначала нажмите 'Утвердить'."))

    def lecture_confirm(self):
        """Утверждение урока -> Создание журнала"""
        super().lecture_confirm()
        # Вызываем метод создания из модели Sheet
        self.env['op.attendance.sheet'].create_sheet_for_session(self)

    def lecture_start(self):
        """Начало урока -> Синхронизация статуса в журнале"""
        super().lecture_start()
        sheet = self._get_linked_sheet()
        if sheet and sheet.state != 'start':
            sheet.write({'state': 'start'})

    def lecture_done(self):
        """Завершение урока -> Закрытие журнала с расчетами"""
        super().lecture_done()
        sheet = self._get_linked_sheet()
        if sheet and sheet.state != 'done':
            # Вызываем именно action_attendance_done, чтобы сработал пересчет оценок в Subject Grades
            sheet.action_attendance_done()

    def lecture_cancel(self):
        """Отмена урока -> Проверка и отмена журнала"""
        sheet = self._get_linked_sheet()
        if sheet:
            # Проверка на оценки находится внутри метода action_attendance_cancel
            sheet.action_attendance_cancel()
        super().lecture_cancel()

    def lecture_edit(self):
        """Редактирование урока -> Возврат журнала в статус 'Урок идет'"""
        super().lecture_edit()
        sheet = self._get_linked_sheet()
        if sheet:
            sheet.write({'state': 'start'})

    def lecture_draft(self):
        """Восстановление урока в Черновик"""
        super().lecture_draft()
        # Журнал при этом остается в статусе 'cancel' (как архив), 
        # при повторном нажатии 'Утвердить' создастся новый или обновится старый.