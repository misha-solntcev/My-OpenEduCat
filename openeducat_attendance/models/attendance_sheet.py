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
    timing = fields.Char(related='session_id.timing', string='Время', store=False)
    classroom_id = fields.Many2one(related='session_id.classroom_id', string='Кабинет', store=True)    
    textbook_image = fields.Image('Учебник', compute='_compute_textbook_image', store=True)    

    # --- ЛОГИКА СОЗДАНИЯ (ТОЛЬКО ШАПКА) ---
    @api.model
    def create_sheet_for_session(self, session):
        sheet = self.search([('session_id', '=', session.id)], limit=1)
        if sheet:
            if sheet.state == 'cancel': sheet.write({'state': 'confirm'})
            return sheet

        register = self.env['op.attendance.register'].sudo().search([
            ('course_id', '=', session.course_id.id),
            ('batch_id', '=', session.batch_id.id)
        ], limit=1)

        return self.create({
            'session_id': session.id,
            'attendance_date': session.start_datetime.date(),
            'register_id': register.id if register else False,
            'state': 'confirm',
            'attendance_line': [] # ПУСТО при создании
        })

    # --- ГЕНЕРАЦИЯ СПИСКА ДЕТЕЙ ---
    def action_generate_lines(self):
        """Создает строки учеников, если их еще нет"""
        for rec in self:
            if not rec.attendance_line:
                students = self.env['op.student'].sudo().search([
                    ('course_detail_ids.course_id', '=', rec.session_id.course_id.id),
                    ('course_detail_ids.batch_id', '=', rec.batch_id.id),
                    ('active', '=', True)
                ])
                lines = [(0, 0, {'student_id': s.id, 'attendance_type_id': False}) for s in students]
                rec.write({'attendance_line': lines})

    # Заполнение статистики по оценкам в Subject Grades после завершения урока
    def _transfer_grades_to_stats(self):
        GradeObj = self.env['op.subject.grades']
        for sheet in self:
            if not sheet.subject_id: continue
            student_ids = sheet.attendance_line.mapped('student_id').ids
            existing = GradeObj.search([('student_id', 'in', student_ids), ('subject_id', '=', sheet.subject_id.id)])
            existing_sids = existing.mapped('student_id').ids
            to_create = [s for s in student_ids if s not in existing_sids]
            if to_create:
                GradeObj.create([{'student_id': s, 'subject_id': sheet.subject_id.id, 'batch_id': sheet.batch_id.id} for s in to_create])
            GradeObj.search([('student_id', 'in', student_ids), ('subject_id', '=', sheet.subject_id.id)]).action_force_recompute()

    # --- СИНХРОНИЗАЦИЯ СТАТУСОВ (Журнал -> Урок) ---
    def action_attendance_start(self):
        """Нажать 'Начать' в Журнале"""
        self.action_generate_lines() # Генерируем детей при старте
        self.write({'state': 'start'})
        if self.session_id and self.session_id.state != 'start':
            self.session_id.write({'state': 'start'})

    def action_attendance_done(self):
        self.write({'state': 'done'})
        if self.session_id and self.session_id.state != 'done':
            self.session_id.write({'state': 'done'})
        # Вызов миграции оценок в Subject Grades (твой код из Шага 4)
        self._transfer_grades_to_stats()

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
        image_cache = {}        
        for r in self:
            if not r.subject_id or not r.course_id:
                r.textbook_image = False
                continue            
            cache_key = (r.subject_id.id, r.course_id.id)            
            if cache_key in image_cache:
                r.textbook_image = image_cache[cache_key]
                continue
            domain = [('subject_ids', 'in', r.subject_id.ids), ('x_image_128', '!=', False)]            
            media = self.env['op.media'].sudo().search(domain + [('course_ids', 'in', r.course_id.ids)], limit=1)            
            if not media:                
                media = self.env['op.media'].sudo().search(domain, limit=1)            
            res_image = media.x_image_128 if media else False                        
            image_cache[cache_key] = res_image
            r.textbook_image = res_image

    @api.model
    def _expand_groups(self, days, domain, order=None):
        return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


    # --- СТАТИСТИКА ПОСЕЩАЕМОСТИ ---
    # Посещаемость
    total_students = fields.Integer(compute='_compute_all_stats', store=True)
    total_present = fields.Integer(compute='_compute_all_stats', store=True)
    total_absent = fields.Integer(compute='_compute_all_stats', store=True)
    attendance_rate = fields.Float(compute='_compute_all_stats', store=True)
    # Оценки
    count_5 = fields.Integer(compute='_compute_all_stats', store=True)
    count_4 = fields.Integer(compute='_compute_all_stats', store=True)
    count_3 = fields.Integer(compute='_compute_all_stats', store=True)
    count_2 = fields.Integer(compute='_compute_all_stats', store=True)
    average_grade_lesson = fields.Float(compute='_compute_all_stats', store=True)

    @api.depends('attendance_line', 'attendance_line.attendance_type_id', 
        'attendance_line.grade_1', 'attendance_line.grade_2', 'attendance_line.grade_3')
    def _compute_all_stats(self):        
        for rec in self:
            total = len(rec.attendance_line)
            present = 0
            absent = 0            
            counts = {5: 0, 4: 0, 3: 0, 2: 0}
            all_marks = []

            for line in rec.attendance_line:                
                if line.present: 
                    present += 1
                elif line.absent: 
                    absent += 1                
                for val in [line.grade_1, line.grade_2, line.grade_3]:
                    if val and 2 <= val <= 5:
                        counts[int(val)] += 1
                        all_marks.append(val)
            
            rec.update({
                'total_students': total,
                'total_present': present,
                'total_absent': absent,
                'attendance_rate': (present / total * 100) if total > 0 else 0.0,
                'count_5': counts[5],
                'count_4': counts[4],
                'count_3': counts[3],
                'count_2': counts[2],
                'average_grade_lesson': sum(all_marks) / len(all_marks) if all_marks else 0.0
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