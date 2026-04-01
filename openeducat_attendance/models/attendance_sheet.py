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

from odoo import api, fields, models


class OpAttendanceSheet(models.Model):
    _name = "op.attendance.sheet"
    _inherit = ["mail.thread"]
    _description = "Attendance Sheet"
    _order = "attendance_date desc"

    name = fields.Char('Name', readonly=True, size=32)
    register_id = fields.Many2one(
        'op.attendance.register', 'Register', required=True,
        tracking=True)
    course_id = fields.Many2one(
        'op.course', related='register_id.course_id', store=True,
        readonly=True)
    batch_id = fields.Many2one(
        'op.batch', 'Batch', related='register_id.batch_id', store=True,
        readonly=True)
    session_id = fields.Many2one('op.session', 'Session')
    attendance_date = fields.Date(
        'Date', required=True, default=lambda self: fields.Date.today(),
        tracking=True)
    attendance_line = fields.One2many(
        'op.attendance.line', 'attendance_id', 'Attendance Line')
    faculty_id = fields.Many2one('op.faculty', 'Faculty')
    active = fields.Boolean(default=True)
    
    # Добавляем поле для темы урока
    lesson_topic = fields.Char(
        'Тема урока', 
        size=256,
        help="Тема урока, которая будет отображаться в оценках по предметам"
    )

    # models/attendance_sheet.py
    subject_id = fields.Many2one('op.subject', string='Предмет', compute='_compute_subject_id', store=True)
    term_id = fields.Many2one('op.academic.term', string='Четверть', compute='_compute_term', store=True)

    @api.depends('session_id.subject_id', 'register_id.subject_id')
    def _compute_subject_id(self):
        for rec in self:
            # Строгая логика: приоритет уроку, если нет - регистру
            rec.subject_id = rec.session_id.subject_id or rec.register_id.subject_id

    @api.depends('attendance_date')
    def _compute_term(self):
        for record in self:
            if record.attendance_date:
                term = self.env['op.academic.term'].search([
                    ('term_start_date', '<=', record.attendance_date),
                    ('term_end_date', '>=', record.attendance_date),
                    ('parent_term', '!=', False)
                ], limit=1)
                record.term_id = term

    state = fields.Selection(
        [('draft', 'Draft'), ('start', 'Attendance Start'),
         ('done', 'Attendance Taken'), ('cancel', 'Cancelled')],
        'Status', default='draft', tracking=True)

    def attendance_draft(self):
        self.state = 'draft'

    def attendance_start(self):
        self.state = 'start'

    def attendance_done(self):
        self.state = 'done'

    def attendance_cancel(self):
        self.state = 'cancel'

    _sql_constraints = [
        ('unique_register_sheet',
         'unique(register_id,session_id,attendance_date)',
         'Sheet must be unique per Register/Session.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            sheet = self.env['ir.sequence'].next_by_code('op.attendance.sheet')
            register = self.env['op.attendance.register']. \
                browse(vals['register_id']).code
            vals['name'] = register + sheet
        return super(OpAttendanceSheet, self).create(vals_list)