##############################################################################
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
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Attendance Sheet"
    _order = "attendance_date desc"

    # Техническое поле (Старый код типа 11А4чAR-AS2358). Оставлен для целостности БД
    name = fields.Char('Name', readonly=True, size=32)

    # 2. Красивый заголовок (Для учителей)
    display_title = fields.Char(
        string='Журнал урока', 
        compute='_compute_display_title', 
        store=True)

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
        'Date', required=True, default=fields.Date.context_today,
        tracking=True)
    attendance_line = fields.One2many(
        'op.attendance.line', 'attendance_id', 'Attendance Line')
    active = fields.Boolean(default=True)
    
    faculty_id = fields.Many2one(
        'op.faculty', 'Faculty', 
        compute='_compute_faculty_id', store=True, readonly=False)

    subject_id = fields.Many2one(
        'op.subject', string='Предмет', compute='_compute_subject_id', store=True)
    
    term_id = fields.Many2one(
        'op.academic.term', string='Четверть', compute='_compute_term', store=True)

    lesson_topic = fields.Char('Тема урока', size=256)

    state = fields.Selection([
        ('draft', 'Запланирован'),
        ('start', 'Урок идет'),
        ('done', 'Проведен'),
        ('cancel', 'Отменен'),
    ], string='Статус', default='draft', tracking=True)

    # --- ЛОГИКА ОТОБРАЖЕНИЯ ИМЕНИ ---
    @api.depends('session_id', 'register_id', 'attendance_date')
    def _compute_display_title(self):
        for rec in self:
            subj = rec.session_id.subject_id.name or rec.register_id.subject_id.name or "Урок"
            batch = rec.batch_id.name or ""
            date_str = rec.attendance_date.strftime('%d.%m.%Y') if rec.attendance_date else ""
            rec.display_title = f"{subj} ({batch}) — {date_str}"

    def _compute_display_name(self):
        """Переопределяем, что Odoo показывает в ссылках и заголовках"""
        for rec in self:
            rec.display_name = rec.display_title or rec.name

    @api.depends('session_id.faculty_id', 'register_id')
    def _compute_faculty_id(self):
        for rec in self:
            if rec.session_id.faculty_id:
                rec.faculty_id = rec.session_id.faculty_id
            elif not rec.faculty_id:
                rec.faculty_id = False

    @api.depends('session_id.subject_id', 'register_id.subject_id')
    def _compute_subject_id(self):
        for rec in self:
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

    def action_attendance_start(self):
        self.write({'state': 'start'})
    def action_attendance_done(self):
        # 1. Сначала выполняем стандартное действие (меняем статус на 'done')
        res = self.write({'state': 'done'})
        
        # 2. Автоматизация для итоговых оценок (Subject Grades)
        GradeObj = self.env['op.subject.grades']
        
        for sheet in self:
            if not sheet.subject_id or not sheet.batch_id:
                continue
                
            # Собираем ID всех учеников в этом журнале
            student_ids = sheet.attendance_line.mapped('student_id')
            
            for student in student_ids:
                # Ищем, есть ли уже карточка итоговых оценок
                grade_card = GradeObj.search([
                    ('student_id', '=', student.id),
                    ('subject_id', '=', sheet.subject_id.id),
                    ('batch_id', '=', sheet.batch_id.id)
                ], limit=1)
                
                # Если карточки нет — создаем её «на лету»
                if not grade_card:
                    grade_card = GradeObj.create({
                        'student_id': student.id,
                        'subject_id': sheet.subject_id.id,
                        'batch_id': sheet.batch_id.id,
                    })
                
                # Запускаем пересчет статистики в этой карточке
                # (используем ваш существующий метод из subject_grades.py)
                grade_card.action_force_recompute()
                
        return res

    def action_attendance_draft(self):
        self.write({'state': 'draft'})

    def action_attendance_cancel(self):
        self.write({'state': 'cancel'})


# --- СЧЕТЧИКИ ПОСЕЩАЕМОСТИ (store=True обязателен для поиска и Pivot) ---
    total_students = fields.Integer(compute='_compute_attendance_stats', 
        store=True, aggregator="sum")
    total_present = fields.Integer(compute='_compute_attendance_stats', 
        store=True, aggregator="sum")
    total_absent = fields.Integer(compute='_compute_attendance_stats', 
        store=True, aggregator="sum")
    attendance_rate = fields.Float(compute='_compute_attendance_stats', 
        store=True, aggregator="avg")

    @api.depends('attendance_line', 'attendance_line.attendance_type_id')
    def _compute_attendance_stats(self):
        for rec in self:
            stats = self.env['op.attendance.line'].get_stats_from_lines(rec.attendance_line)
            rec.total_students = stats['total']
            rec.total_present = stats['present']
            rec.total_absent = stats['absent']
            rec.attendance_rate = stats['rate']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # name теперь будет просто порядковым номером из последовательности
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('op.attendance.sheet') or '/'
        return super(OpAttendanceSheet, self).create(vals_list)

    # Авто-заполнение данных при выборе урока вручную (если зашли не из расписания)
    @api.onchange('session_id')
    def onchange_session_id(self):
        if self.session_id:
            self.attendance_date = self.session_id.start_datetime.date()
            self.faculty_id = self.session_id.faculty_id            
            register = self.env['op.attendance.register'].search([
                ('course_id', '=', self.session_id.course_id.id),
                ('batch_id', '=', self.session_id.batch_id.id)
            ], limit=1)
            if register:
                self.register_id = register

