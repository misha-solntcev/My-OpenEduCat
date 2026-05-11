# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError  

class OpSession(models.Model):
    _inherit = "op.session"

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---

    def _get_linked_sheet(self):
        """Поиск связанного журнала"""
        return self.env['op.attendance.sheet'].sudo().search([('session_id', '=', self.id)], limit=1)

    def get_attendance(self):
        """Метод для кнопки 'Журнал урока' (Stat-button)"""
        self.ensure_one()
        if self.state == 'cancel':
            raise ValidationError(_("Нельзя открыть журнал для отмененного урока."))
        
        sheet = self._get_linked_sheet()
        
        # ЛОГИКА "ПО ТРЕБОВАНИЮ": если завуч утвердил урок, но журнал почему-то не создался
        if not sheet:
            if self.state == 'draft':
                raise ValidationError(_("Сначала утвердите урок, чтобы создать журнал."))
            # Создаем "на лету"
            sheet = self.env['op.attendance.sheet'].create_sheet_for_session(self)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'op.attendance.sheet',
            'view_mode': 'form',
            'res_id': sheet.id,
            'target': 'current',
        }

    # --- КАСКАДНАЯ ЛОГИКА СТАТУСОВ (СИНХРОНИЗАЦИЯ) ---

    def lecture_confirm(self):
        """Этап 1: Утверждение. Создаем только 'шапку' журнала."""
        super().lecture_confirm()
        # Метод в Sheet сам проверит, есть ли он, или восстановит из cancel
        self.env['op.attendance.sheet'].create_sheet_for_session(self)

    def lecture_start(self):
        """Этап 2: Старт. Если прыгнули из черновика — сначала Утверждаем."""
        if self.state == 'draft':
            self.lecture_confirm()
            
        super().lecture_start()
        sheet = self._get_linked_sheet()
        if sheet:
            # action_attendance_start в модели Sheet сменит статус и СОЗДАСТ список детей
            sheet.action_attendance_start()

    def lecture_done(self):
        """Этап 3: Завершение. Если прыгнули через этапы — проходим их все."""
        if self.state in ['draft', 'confirm']:
            self.lecture_start()
            
        super().lecture_done()
        sheet = self._get_linked_sheet()
        if sheet:
            # action_attendance_done закроет журнал и перенесет оценки в статистику
            sheet.action_attendance_done()

    def lecture_cancel(self):
        """Отмена: Проверка оценок и отмена журнала."""
        sheet = self._get_linked_sheet()
        if sheet:
            # Вызываем метод в Sheet, так как в нем встроена проверка на наличие оценок
            sheet.action_attendance_cancel()
        super().lecture_cancel()

    def lecture_edit(self):
        """Редактирование: Возврат в 'Урок идет'."""
        super().lecture_edit()
        sheet = self._get_linked_sheet()
        if sheet:
            sheet.write({'state': 'start'})

    def lecture_draft(self):
        """Сброс в черновик: Журнал уходит в Отмену (архив)."""
        super().lecture_draft()
        sheet = self._get_linked_sheet()
        if sheet:
            sheet.write({'state': 'cancel'})