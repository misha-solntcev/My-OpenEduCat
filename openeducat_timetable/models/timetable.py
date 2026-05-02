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

import pytz
import calendar
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class OpSession(models.Model):
    _name = "op.session"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Sessions"
    _order = "start_datetime asc, batch_id, id"

    name = fields.Char(compute='_compute_name', string='Name', store=True)
    timing = fields.Char(compute='_compute_timing', string='Session Timing')
    
    start_datetime = fields.Datetime('Start Time', required=True, default=fields.Datetime.now, tracking=True)
    end_datetime = fields.Datetime('End Time', required=True, tracking=True)
    
    course_id = fields.Many2one('op.course', 'Course', required=True, tracking=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', required=True, tracking=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True, tracking=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, tracking=True)
    classroom_id = fields.Many2one('op.classroom', 'Classroom', tracking=True)
    
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    state = fields.Selection([
        ('draft', 'Черновик'), 
        ('confirm', 'Утвержден'),
        ('start', 'Идет урок'),
        ('done', 'Проведен'), 
        ('cancel', 'Отменен')],
        string='Status', default='draft', tracking=True)

    # Дни недели для Канбана и фильтрации
    days = fields.Selection([
        ('monday', 'Понедельник'),
        ('tuesday', 'Вторник'),
        ('wednesday', 'Среда'),
        ('thursday', 'Четверг'),
        ('friday', 'Пятница'),
        ('saturday', 'Суббота'),
        ('sunday', 'Воскресенье')],
        string='Day of Week', compute='_compute_day_info', store=True, group_expand='_expand_groups'
    )

    # Поле для Record Rules (оптимизировано)
    user_ids = fields.Many2many('res.users', string='Users', compute='_compute_user_ids', store=True)

    @api.model
    def _expand_groups(self, days, domain, order=None):
        return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    @api.depends('start_datetime', 'end_datetime', 'faculty_id', 'subject_id')
    def _compute_name(self):
        tz = pytz.timezone('Europe/Moscow')
        for rec in self:
            if rec.start_datetime and rec.end_datetime:                
                s = rec.start_datetime.astimezone(tz).strftime('%H:%M')
                e = rec.end_datetime.astimezone(tz).strftime('%H:%M')
                rec.name = f"{rec.subject_id.name} ({rec.faculty_id.name}) {s} - {e}"
            else:
                rec.name = "Новое занятие..."

    @api.depends('start_datetime', 'end_datetime')
    def _compute_timing(self):
        tz = pytz.timezone('Europe/Moscow')
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                s = rec.start_datetime.astimezone(tz).strftime('%H:%M')
                e = rec.end_datetime.astimezone(tz).strftime('%H:%M')
                rec.timing = f"{s} - {e}"
            else:
                rec.timing = ""
    @api.depends('start_datetime')
    def _compute_day_info(self):
        # Строгое соответствие ключам в field.Selection
        days_map = {
            0: 'monday', 1: 'tuesday', 2: 'wednesday', 
            3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'
        }
        for record in self:
            if record.start_datetime:
                # weekday() всегда возвращает число 0-6
                day_index = record.start_datetime.weekday()
                record.days = days_map.get(day_index)
            else:
                record.days = False

    @api.depends('batch_id', 'faculty_id')
    def _compute_user_ids(self):        
        for session in self.sudo():
            u_ids = []            
            
            if session.faculty_id.user_id:
                u_ids.append(session.faculty_id.user_id.id)            
            
            students = self.env['op.student'].sudo().search([
                ('course_detail_ids.batch_id', '=', session.batch_id.id)
            ])            
            
            student_user_ids = students.mapped('user_id').ids
            u_ids.extend(student_user_ids)            
            
            session.user_ids = [(6, 0, list(set(filter(None, u_ids))))]
    
    
    def lecture_confirm(self):
        self.write({'state': 'confirm'})
        self._create_attendance_sheet()
    
    def lecture_start(self):       
        self.write({'state': 'start'})
        sheets = self.env['op.attendance.sheet'].search([('session_id', 'in', self.ids)])
        sheets.write({'state': 'start'})

    def lecture_done(self):
        self.write({'state': 'done'})
        sheets = self.env['op.attendance.sheet'].search([('session_id', 'in', self.ids)])
        for sheet in sheets:
            if sheet.state != 'done':
                sheet.action_attendance_done()

    def lecture_cancel(self):
        for record in self:            
            sheet = self.env['op.attendance.sheet'].search([('session_id', '=', record.id)], limit=1)
            if sheet:                
                marks = sheet.attendance_line.filtered(lambda l: l.grade_1 or l.grade_2 or l.grade_3)
                if marks:
                    raise ValidationError(_("Нельзя отменить урок, по которому уже выставлены оценки в журнале!"))
                sheet.write({'state': 'cancel'})
            record.write({'state': 'cancel'})

    def lecture_draft(self):
        """Кнопка 'Восстановить': из Отменен -> в Черновик"""
        self.write({'state': 'draft'})
        sheets = self.env['op.attendance.sheet'].search([('session_id', 'in', self.ids)])
        if sheets:
            sheets.write({'state': 'confirm'})

    def lecture_edit(self):
        """Кнопка 'Редактировать': из Проведен -> назад в Идет урок.
        Синхронно возвращает в работу и связанный журнал."""
        self.write({'state': 'start'})
        sheets = self.env['op.attendance.sheet'].search([('session_id', 'in', self.ids)])
        if sheets:            
            sheets.write({'state': 'start'})

    def _create_attendance_sheet(self):
        """Оптимизированное создание журнала в статусе 'confirm'"""
        AttendanceSheet = self.env['op.attendance.sheet']
        for record in self:
            if AttendanceSheet.search_count([('session_id', '=', record.id)]):
                continue
            
            students = self.env['op.student'].search([
                ('course_detail_ids.course_id', '=', record.course_id.id),
                ('course_detail_ids.batch_id', '=', record.batch_id.id),
                ('active', '=', True)
            ])
            register = self.env['op.attendance.register'].search([
                ('course_id', '=', record.course_id.id),
                ('batch_id', '=', record.batch_id.id)
            ], limit=1)
            present_type = self.env['op.attendance.type'].search([('present', '=', True)], limit=1)

            AttendanceSheet.create({
                'session_id': record.id,
                'attendance_date': record.start_datetime.date(),
                'faculty_id': record.faculty_id.id,
                'register_id': register.id if register else False,
                'state': 'confirm', # Журнал сразу "Утвержден"
                'attendance_line': [(0, 0, {
                    'student_id': s.id,
                    'attendance_type_id': present_type.id if present_type else False,
                }) for s in students]
            })

    @api.constrains('start_datetime', 'end_datetime')
    def _check_date_time(self):
        for rec in self:
            if rec.start_datetime >= rec.end_datetime:
                raise ValidationError(_('Дата окончания должна быть позже даты начала.'))

    @api.constrains('faculty_id', 'start_datetime', 'end_datetime', 'classroom_id', 'batch_id')
    def _check_conflicts(self):
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('start_datetime', '<', rec.end_datetime),
                ('end_datetime', '>', rec.start_datetime),
                ('state', '!=', 'cancel'),
            ]
            
            if self.search_count(domain + [('faculty_id', '=', rec.faculty_id.id)]):
                raise ValidationError(_('Преподаватель %s уже занят в этот период!') % rec.faculty_id.name)
            
            if self.search_count(domain + [('batch_id', '=', rec.batch_id.id)]):
                raise ValidationError(_('Группа %s уже имеет занятие в этот период!') % rec.batch_id.name)

    @api.onchange('course_id')
    def _onchange_course_id(self):
        self.batch_id = False
        self.subject_id = False
        if self.course_id:
            return {'domain': {'subject_id': [('id', 'in', self.course_id.subject_ids.ids)]}}