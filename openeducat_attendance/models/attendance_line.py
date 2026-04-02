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


class OpAttendanceLine(models.Model):
    _name = "op.attendance.line"
    _inherit = ["mail.thread"]
    _rec_name = "attendance_id"
    _description = "Attendance Lines"
    _order = "attendance_date desc"

    # --- СВЯЗИ ---
    attendance_id = fields.Many2one(
        'op.attendance.sheet', 'Attendance Sheet', required=True,
        tracking=True, ondelete="cascade")
    student_id = fields.Many2one(
        'op.student', 'Student', required=True, tracking=True)
    register_id = fields.Many2one(
        related='attendance_id.register_id', store=True, readonly=True)
    
    # --- ДАННЫЕ ВЕДОМОСТИ (Берем из родительской записи op.attendance.sheet) ---
    attendance_date = fields.Date(
        'Date', related='attendance_id.attendance_date', store=True,
        readonly=True, tracking=True)
    
    # ПРЕДМЕТ: Теперь берется строго из ведомости (которая берет его из урока или регистра)
    subject_id = fields.Many2one(
        'op.subject', string='Предмет', 
        related='attendance_id.subject_id', store=True, readonly=True)

    # ПЕРИОДЫ: Теперь берутся строго из ведомости
    term_id = fields.Many2one(
        'op.academic.term', string='Четверть', 
        related='attendance_id.term_id', store=True, readonly=True)
    
    academic_year_id = fields.Many2one(
        'op.academic.year', string='Учебный год', 
        related='term_id.academic_year_id', store=True, readonly=True)

    parent_term_id = fields.Many2one(
        'op.academic.term', string='Полугодие', 
        related='term_id.parent_term', store=True, readonly=True)

    course_id = fields.Many2one(
        'op.course', 'Course',
        related='attendance_id.register_id.course_id', store=True, readonly=True)
    
    batch_id = fields.Many2one(
        'op.batch', 'Batch',
        related='attendance_id.register_id.batch_id', store=True, readonly=True)

    faculty_id = fields.Many2one(
        'op.faculty', 'Faculty', 
        related='attendance_id.faculty_id', store=True, readonly=True)

    lesson_topic = fields.Char(
        'Lesson Topic', related='attendance_id.lesson_topic', store=True, readonly=False)

    # --- ОЦЕНКИ ---
    grade_1 = fields.Float('Оценка 1', aggregator="avg")
    grade_2 = fields.Float('Оценка 2', aggregator="avg")
    grade_3 = fields.Float('Оценка 3', aggregator="avg")

    # --- СТАТУС ПРИСУТСТВИЯ ---
    present = fields.Boolean('Present', tracking=True, default=True)
    excused = fields.Boolean('Absent Excused', tracking=True)
    absent = fields.Boolean('Absent Unexcused', tracking=True)
    late = fields.Boolean('Late', tracking=True)
    remark = fields.Char('Remark', size=256, tracking=True)
    active = fields.Boolean(default=True)
    attendance_type_id = fields.Many2one('op.attendance.type', 'Attendance Type')

    _sql_constraints = [
        ('unique_student',
         'unique(student_id,attendance_id,attendance_date)',
         'Student must be unique per Attendance.'),
    ]

    # --- ЛОГИКА ИНТЕРФЕЙСА ---
    @api.onchange('attendance_type_id')
    def onchange_attendance_type(self):
        if self.attendance_type_id:
            self.present = self.attendance_type_id.present
            self.excused = self.attendance_type_id.excused
            self.absent = self.attendance_type_id.absent
            self.late = self.attendance_type_id.late

    @api.onchange('present')
    def onchange_present(self):
        if self.present:
            self.late = self.excused = self.absent = False

    @api.onchange('absent')
    def onchange_absent(self):
        if self.absent:
            self.present = self.late = self.excused = False

    @api.onchange('excused')
    def onchange_excused(self):
        if self.excused:
            self.present = self.late = self.absent = False

    @api.onchange('late')
    def onchange_late(self):
        if self.late:
            self.present = self.excused = self.absent = False