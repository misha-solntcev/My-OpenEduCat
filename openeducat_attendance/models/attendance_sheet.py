from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OpAttendanceSheet(models.Model):
    _name = "op.attendance.sheet"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Attendance Sheet"
    _order = "start_datetime asc, batch_id, id"

    # --- ПОЛЯ ---
    name = fields.Char('Name', readonly=True, size=32)
    display_title = fields.Char(string='Журнал урока', compute='_compute_display_title', store=True)
    
    register_id = fields.Many2one('op.attendance.register', 'Register', required=True, tracking=True)
    course_id = fields.Many2one('op.course', related='register_id.course_id', store=True, readonly=True)
    batch_id = fields.Many2one('op.batch', 'Batch', related='register_id.batch_id', store=True, readonly=True)
    session_id = fields.Many2one('op.session', 'Session', ondelete='cascade')
    
    start_datetime = fields.Datetime(related='session_id.start_datetime', string='Начало урока', store=True, index=True)
    attendance_date = fields.Date('Date', required=True, default=fields.Date.context_today, tracking=True)
    
    faculty_id = fields.Many2one('op.faculty', related='session_id.faculty_id', 
        string='Faculty', store=True, readonly=True, index=True)
    subject_id = fields.Many2one('op.subject', related='session_id.subject_id', 
        string='Предмет', store=True, readonly=True, index=True)
    term_id = fields.Many2one('op.academic.term', string='Четверть', 
        compute='_compute_term', store=True)
    
    lesson_topic = fields.Char('Тема урока', size=256)
    state = fields.Selection([
        ('confirm', 'Утвержден'),
        ('start', 'Урок идет'),
        ('done', 'Проведен'),
        ('cancel', 'Отменен'),
    ], string='Статус', default='confirm', tracking=True)

    active = fields.Boolean(default=True)
    attendance_line = fields.One2many('op.attendance.line', 'attendance_id', 'Attendance Line')
    
    # Визуальные поля
    days = fields.Selection(related='session_id.days', store=True, readonly=True, group_expand='_expand_groups')
    timing = fields.Char(related='session_id.timing', string='Время', store=True)
    classroom_id = fields.Many2one(related='session_id.classroom_id', string='Кабинет', store=True)    
    textbook_image = fields.Image('Учебник', compute='_compute_textbook_image', store=True)    

    # --- ЛОГИКА СОЗДАНИЯ ЖУРНАЛА (Вызывается из OpSession) ---
    @api.model
    def create_sheet_for_session(self, session):
        """Метод автоматического создания журнала при утверждении урока"""
        if self.search_count([('session_id', '=', session.id)]):
            return False

        # Ищем регистр для этого курса и группы
        register = self.env['op.attendance.register'].sudo().search([
            ('course_id', '=', session.course_id.id),
            ('batch_id', '=', session.batch_id.id)
        ], limit=1)

        # Ищем всех активных студентов в этой группе
        students = self.env['op.student'].sudo().search([
            ('course_detail_ids.course_id', '=', session.course_id.id),
            ('course_detail_ids.batch_id', '=', session.batch_id.id),
            ('active', '=', True)
        ])

        # Тип посещаемости по умолчанию (Присутствует)
        present_type = self.env['op.attendance.type'].sudo().search([('present', '=', True)], limit=1)

        return self.create({
            'session_id': session.id,
            'attendance_date': session.start_datetime.date(),
            'faculty_id': session.faculty_id.id,
            'register_id': register.id if register else False,
            'state': 'confirm',
            'attendance_line': [(0, 0, {
                'student_id': s.id,
                'attendance_type_id': present_type.id if present_type else False,
            }) for s in students]
        })

    # --- СИНХРОНИЗАЦИЯ (Журнал -> Урок) ---
    def action_attendance_start(self):
        """Нажать 'Начать' в Журнале"""
        self.write({'state': 'start'})
        if self.session_id and self.session_id.state != 'start':
            self.session_id.write({'state': 'start'})

    def action_attendance_done(self):
        """Нажать 'Завершить' в Журнале (с логикой оценок)"""
        self.write({'state': 'done'})
        if self.session_id and self.session_id.state != 'done':
            self.session_id.write({'state': 'done'})
        
        # --- Твоя логика расчета оценок ---
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

    def action_attendance_cancel(self):
        """Нажать 'Отменить' в Журнале"""
        for rec in self:
            marks = rec.attendance_line.filtered(lambda l: l.grade_1 or l.grade_2 or l.grade_3)
            if marks:
                raise ValidationError(_("Нельзя отменить журнал [%s], так как в нем есть оценки!") % rec.display_title)
            rec.write({'state': 'cancel'})
            if rec.session_id and rec.session_id.state != 'cancel':
                rec.session_id.write({'state': 'cancel'})

    def action_attendance_edit(self):
        """Кнопка 'Редактировать' в Журнале"""
        self.write({'state': 'start'})
        if self.session_id and self.session_id.state != 'start':
            self.session_id.write({'state': 'start'})

    def action_attendance_confirm(self):
        """Восстановление журнала"""
        self.write({'state': 'confirm'})
        if self.session_id and self.session_id.state != 'confirm':
            self.session_id.write({'state': 'confirm'})

    # --- ВЫЧИСЛЯЕМЫЕ МЕТОДЫ ---
    @api.depends('session_id', 'register_id', 'attendance_date')
    def _compute_display_title(self):
        for rec in self:
            subj = rec.session_id.subject_id.name or rec.register_id.subject_id.name or "Урок"
            batch = rec.batch_id.name or ""
            date_str = rec.attendance_date.strftime('%d.%m.%Y') if rec.attendance_date else ""
            rec.display_title = f"{subj} ({batch}) — {date_str}"

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.display_title or rec.name

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

    @api.depends('subject_id', 'course_id')    
    def _compute_textbook_image(self):
        for r in self:
            if not r.subject_id or not r.course_id:
                r.textbook_image = False
                continue
            domain = [('subject_ids', 'in', r.subject_id.ids), ('x_image_128', '!=', False)]
            media = self.env['op.media'].sudo().search(domain + [('course_ids', 'in', r.course_id.ids)], limit=1)
            if not media:
                media = self.env['op.media'].sudo().search(domain, limit=1)
            r.textbook_image = media.x_image_128 if media else False

    @api.model
    def _expand_groups(self, days, domain, order=None):
        return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # --- СТАТИСТИКА ПОСЕЩАЕМОСТИ ---
    total_students = fields.Integer(compute='_compute_attendance_stats', store=True)
    total_present = fields.Integer(compute='_compute_attendance_stats', store=True)
    total_absent = fields.Integer(compute='_compute_attendance_stats', store=True)
    attendance_rate = fields.Float(compute='_compute_attendance_stats', store=True)

    @api.depends('attendance_line', 'attendance_line.attendance_type_id')
    def _compute_attendance_stats(self):
        for rec in self:
            stats = self.env['op.attendance.line'].get_stats_from_lines(rec.attendance_line)
            rec.total_students = stats['total']
            rec.total_present = stats['present']
            rec.total_absent = stats['absent']
            rec.attendance_rate = stats['rate']

    # --- СТАТИСТИКА ОЦЕНОК ---
    count_5 = fields.Integer(compute='_compute_lesson_stats', store=True)
    count_4 = fields.Integer(compute='_compute_lesson_stats', store=True)
    count_3 = fields.Integer(compute='_compute_lesson_stats', store=True)
    count_2 = fields.Integer(compute='_compute_lesson_stats', store=True)
    average_grade_lesson = fields.Float(compute='_compute_lesson_stats', store=True)

    @api.depends('attendance_line.grade_1', 'attendance_line.grade_2', 'attendance_line.grade_3')
    def _compute_lesson_stats(self):
        for rec in self:
            stats = self.env['op.attendance.line'].get_stats_from_lines(rec.attendance_line)
            rec.update({
                'count_5': stats['counts'][5],
                'count_4': stats['counts'][4],
                'count_3': stats['counts'][3],
                'count_2': stats['counts'][2],
                'average_grade_lesson': stats['avg']
            })

    # --- МАССОВЫЕ ДЕЙСТВИЯ ---
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('op.attendance.sheet') or '/'
        return super(OpAttendanceSheet, self).create(vals_list)

    def action_mass_set_attendance(self):
        self.ensure_one()
        if self.state in ('done', 'cancel'): return
        target_name = self.env.context.get('set_name')
        if not target_name: return
        target_type = self.env['op.attendance.type'].search([('name', '=', target_name)], limit=1)
        if target_type:            
            self.attendance_line.write({'attendance_type_id': target_type.id})           

    def action_reset_attendance_sheet(self):
        self.attendance_line.action_clear_line_data()