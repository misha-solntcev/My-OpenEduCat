###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import fields, models, api

class OpSession(models.Model):
    _inherit = "op.session"

    def get_attendance(self):
        self.ensure_one()
        # 1. Ищем, есть ли уже журнал для этого урока
        sheet = self.env['op.attendance.sheet'].search([('session_id', '=', self.id)], limit=1)
        
        if not sheet:
            # 2. Если журнала нет, автоматически ищем "Регистр" (папку) этого класса
            register = self.env['op.attendance.register'].search([
                ('course_id', '=', self.course_id.id),
                ('batch_id', '=', self.batch_id.id)
            ], limit=1)

            # 3. Создаем новый журнал урока
            sheet = self.env['op.attendance.sheet'].create({
                'session_id': self.id,
                'register_id': register.id if register else False,
                'attendance_date': self.start_datetime.date(),
                'faculty_id': self.faculty_id.id,
                'state': 'start', # Сразу переводим в статус "Урок идет"
            })
            # 4. Автоматически наполняем списком учеников
            sheet._fill_student_lines()

        # 5. Открываем форму журнала
        return {
            'name': 'Журнал урока',
            'type': 'ir.actions.act_window',
            'res_model': 'op.attendance.sheet',
            'view_mode': 'form',
            'res_id': sheet.id,
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'}, # Сразу открываем на редактирование
        }