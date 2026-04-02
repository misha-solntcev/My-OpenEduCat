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

from odoo import fields, models


class OpSession(models.Model):
    _inherit = "op.session"

    attendance_sheet = fields.One2many('op.attendance.sheet',
                                       'session_id', string='Session')

    def get_attendance(self, context=None):
        self.ensure_one() # Убеждаемся, что работаем с одним уроком
        
        sheet = self.env['op.attendance.sheet'].search(
            [('session_id', '=', self.id)])
        register = self.env['op.attendance.register'].search(
            [('course_id', '=', self.course_id.id),
             ('batch_id', '=', self.batch_id.id)], limit=1)

        # Формируем общий контекст, чтобы не дублировать код
        common_context = {
            'default_session_id': self.id,
            'default_register_id': register.id if register else False,
            'default_subject_id': self.subject_id.id,
            'default_faculty_id': self.faculty_id.id,
            'default_attendance_date': self.start_datetime.date(),
        }

        if sheet:
            if len(sheet) == 1:
                view_id = self.env.ref('openeducat_attendance.view_op_attendance_sheet_form').id
                return {
                    'name': 'Attendance Sheet',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'op.attendance.sheet',
                    'view_id': view_id,
                    'res_id': sheet.id,
                    'target': 'current',
                    'context': common_context,
                }
            else:
                action = self.env.ref('openeducat_attendance.act_open_op_attendance_sheet_view').read()[0]
                action['domain'] = [('session_id', '=', self.id)]
                action['context'] = common_context
                return action
        else:
            # Если ведомости еще нет - открываем пустую форму с предустановленными данными
            view_id = self.env.ref('openeducat_attendance.view_op_attendance_sheet_form').id
            return {
                'name': 'Attendance Sheet',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'op.attendance.sheet',
                'view_id': view_id,
                'target': 'current',
                'context': common_context,
            }