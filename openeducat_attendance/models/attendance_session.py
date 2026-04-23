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

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError  # ОБЯЗАТЕЛЬНО ДОБАВЬ ЭТО

class OpSession(models.Model):
    _inherit = "op.session"

    def get_attendance(self):
        self.ensure_one()
        
        # 1. Если урок отменен — показываем красивое уведомление (не ошибку)
        if self.state == 'cancel':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Урок отменен'),
                    'message': _('Для отмененного занятия журнал недоступен.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # 2. Ищем существующую ведомость (через sudo, чтобы точно найти)
        AttendanceSheet = self.env['op.attendance.sheet'].sudo()
        sheet = AttendanceSheet.search([('session_id', '=', self.id)], limit=1)
        
        # 3. Если ведомости нет, но урок подтвержден/завершен — создаем её (Fix для старых данных)
        if not sheet and self.state in ['confirm', 'done']:
            # Собираем данные для создания
            register = self.env['op.attendance.register'].sudo().search([
                ('course_id', '=', self.course_id.id),
                ('batch_id', '=', self.batch_id.id)
            ], limit=1)
            
            students = self.env['op.student'].sudo().search([
                ('course_detail_ids.course_id', '=', self.course_id.id),
                ('course_detail_ids.batch_id', '=', self.batch_id.id)
            ])
            
            present_type = self.env['op.attendance.type'].sudo().search([('present', '=', True)], limit=1)

            # Создаем журнал автоматически
            sheet = AttendanceSheet.create({
                'session_id': self.id,
                'attendance_date': self.start_datetime.date(),
                'faculty_id': self.faculty_id.id,
                'register_id': register.id if register else False,
                'attendance_line': [(0, 0, {
                    'student_id': s.id,
                    'attendance_type_id': present_type.id if present_type else False,
                }) for s in students],
                'state': 'draft',
            })

        # 4. Финальная проверка перед открытием
        if sheet:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'op.attendance.sheet',
                'view_mode': 'form',
                'res_id': sheet.id,
                'target': 'current',
            }
        else:
            # Сюда попадем, только если self.state == 'draft'
            raise ValidationError(_("Сначала нажмите кнопку 'Утвердить' в расписании, чтобы создать журнал урока."))