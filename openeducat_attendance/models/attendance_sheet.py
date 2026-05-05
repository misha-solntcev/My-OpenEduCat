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
        ('confirm', 'Утвержден'),
        ('start', 'Урок идет'),
        ('done', 'Проведен'),
        ('cancel', 'Отменен'),
    ], string='Статус', default='confirm', tracking=True)

    days = fields.Selection(
        related='session_id.days', 
        store=True, 
        readonly=True, 
        group_expand='_expand_groups'
    )

    timing = fields.Char(related='session_id.timing', string='Время', store=True)
    @api.model
    def _expand_groups(self, days, domain, order=None):
        # Этот список задает ЖЕСТКИЙ порядок колонок в Канбане
        return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
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
        """Начать урок"""
        self.write({'state': 'start'})
        if self.session_id and self.session_id.state != 'start':
            self.session_id.write({'state': 'start'})

    def action_attendance_done(self):
        """Завершить урок (Синхронно с расписанием + расчет итогов)"""
        res = self.write({'state': 'done'})
        if self.session_id and self.session_id.state != 'done':
            self.session_id.write({'state': 'done'})        
        
        GradeObj = self.env['op.subject.grades']
        for sheet in self:
            if not sheet.subject_id or not sheet.batch_id: continue
            student_ids = sheet.attendance_line.mapped('student_id')
            existing_cards = GradeObj.search([
                ('student_id', 'in', student_ids.ids),
                ('subject_id', '=', sheet.subject_id.id),
                ('batch_id', '=', sheet.batch_id.id)
            ])
            existing_student_ids = existing_cards.mapped('student_id').ids
            missing_students = student_ids.filtered(lambda s: s.id not in existing_student_ids)
            
            if missing_students:
                GradeObj.create([{
                    'student_id': s.id, 'subject_id': sheet.subject_id.id, 'batch_id': sheet.batch_id.id,
                } for s in missing_students])            
            
            all_cards = GradeObj.search([
                ('student_id', 'in', student_ids.ids),
                ('subject_id', '=', sheet.subject_id.id),
                ('batch_id', '=', sheet.batch_id.id)
            ])
            all_cards.action_force_recompute()
        return res

    def action_attendance_edit(self):
        """Редактировать: возврат в 'Идет урок' для правок"""
        self.write({'state': 'start'})
        if self.session_id:
            self.session_id.write({'state': 'start'})

    def action_attendance_confirm(self):
        """Восстановить: из Отменен -> в Утвержден"""
        self.write({'state': 'confirm'})
        if self.session_id:
            self.session_id.write({'state': 'confirm'})

    def action_attendance_cancel(self):
        """Отмена из журнала с проверкой на оценки"""
        marks = self.attendance_line.filtered(lambda l: l.grade_1 or l.grade_2 or l.grade_3)
        if marks:
            raise ValidationError(_("В журнале есть оценки. Удалите их перед отменой."))
        self.write({'state': 'cancel'})
        if self.session_id:
            self.session_id.write({'state': 'cancel'})    


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


    # Статистика по оценкам для Канбана (считает все 3 оценки вместе)

    # Поля для Канбана (обязательно store=True)
    count_5 = fields.Integer(compute='_compute_lesson_stats', store=True)
    count_4 = fields.Integer(compute='_compute_lesson_stats', store=True)
    count_3 = fields.Integer(compute='_compute_lesson_stats', store=True)
    count_2 = fields.Integer(compute='_compute_lesson_stats', store=True)
    average_grade_lesson = fields.Float(compute='_compute_lesson_stats', store=True, digits=(1, 2))

    @api.depends('attendance_line.grade_1', 'attendance_line.grade_2', 'attendance_line.grade_3', 'attendance_line.attendance_type_id')
    def _compute_lesson_stats(self):
        for rec in self:
            # Вызываем ваш метод, который уже умеет собирать все оценки 1, 2, 3 вместе
            stats = self.env['op.attendance.line'].get_stats_from_lines(rec.attendance_line)
            
            rec.update({
                'count_5': stats['counts'][5],
                'count_4': stats['counts'][4],
                'count_3': stats['counts'][3],
                'count_2': stats['counts'][2],
                'average_grade_lesson': stats['avg']
            })


    # ---- МАССОВЫЕ ДЕЙСТВИЯ ----
    def action_mass_set_attendance(self):
        """Оптимизированная установка статуса"""
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            return

        target_name = self.env.context.get('set_name')
        if not target_name:
            return

        target_type = self.env['op.attendance.type'].search([('name', '=', target_name)], limit=1)
        
        if target_type:            
            self.attendance_line.write({'attendance_type_id': target_type.id})           
            