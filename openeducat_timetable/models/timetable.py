from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class OpSession(models.Model):
    _name = "op.session"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Sessions"
    _order = "start_datetime desc"

    # --- ПОЛЯ ---
    start_datetime = fields.Datetime(
        'Start Time', required=True, index=True, tracking=True,
        default=fields.Datetime.now)
    
    end_datetime = fields.Datetime(
        'End Time', required=True, index=True, tracking=True,
        default=lambda self: fields.Datetime.now() + timedelta(minutes=40))
    
    faculty_id = fields.Many2one('op.faculty', 'Faculty', required=True, index=True, tracking=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True, index=True, tracking=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, index=True, tracking=True)
    course_id = fields.Many2one('op.course', 'Course', required=True, index=True)
    classroom_id = fields.Many2one('op.classroom', 'Classroom', index=True, tracking=True)

    name = fields.Char(compute='_compute_name', string='Name', store=False)
    timing = fields.Char(compute='_compute_timing', string='Session Timing', store=False)
    state = fields.Selection([
        ('draft', 'Черновик'), 
        ('confirm', 'Утвержден'),
        ('start', 'Идет урок'),
        ('done', 'Проведен'), 
        ('cancel', 'Отменен')],
        string='Status', default='draft', tracking=True, index=True)

    active = fields.Boolean(default=True)
    color = fields.Integer('Color Index', default=0)
    user_ids = fields.Many2many('res.users', string='Allowed Users', compute='_compute_user_ids', store=True)
    days = fields.Selection([
        ('monday', 'Понедельник'), ('tuesday', 'Вторник'), ('wednesday', 'Среда'),
        ('thursday', 'Четверг'), ('friday', 'Пятница'), ('saturday', 'Суббота'),
        ('sunday', 'Воскресенье')],
        string='Day of Week', compute='_compute_day_info', store=True, group_expand='_expand_groups'
    )

    # --- ФОРМАТИРОВАНИЕ БЕЗ СЕКУНД ---
    @api.depends('start_datetime', 'end_datetime', 'faculty_id', 'subject_id')
    def _compute_name(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                # strftime('%H:%M') гарантирует отсутствие секунд в названии
                s = fields.Datetime.context_timestamp(rec, rec.start_datetime).strftime('%H:%M')
                e = fields.Datetime.context_timestamp(rec, rec.end_datetime).strftime('%H:%M')
                rec.name = f"{rec.subject_id.name or ''} ({rec.faculty_id.name or ''}) {s}-{e}"
            else:
                rec.name = "/"

    @api.depends('start_datetime', 'end_datetime')
    def _compute_timing(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                s = fields.Datetime.context_timestamp(rec, rec.start_datetime).strftime('%H:%M')
                e = fields.Datetime.context_timestamp(rec, rec.end_datetime).strftime('%H:%M')
                rec.timing = f"{s} - {e}"
            else:
                rec.timing = ""


    def lecture_confirm(self):
        self.write({'state': 'confirm'})

    def lecture_start(self):
        self.write({'state': 'start'})

    def lecture_done(self):
        self.write({'state': 'done'})

    def lecture_cancel(self):
        self.write({'state': 'cancel'})

    def lecture_draft(self):
        self.write({'state': 'draft'})

    def lecture_edit(self):
        self.write({'state': 'start'})

    # --- ВСПОМОГАТЕЛЬНОЕ ---
    @api.model
    def _expand_groups(self, _days, _domain, _order=None):
        return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    @api.depends('start_datetime')
    def _compute_day_info(self):
        days_map = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'}
        for record in self:
            record.days = days_map.get(record.start_datetime.weekday()) if record.start_datetime else False

    @api.depends('batch_id', 'faculty_id')
    def _compute_user_ids(self):        
        for session in self:
            u_ids = set()
            if session.faculty_id.user_id:
                u_ids.add(session.faculty_id.user_id.id)
            if session.batch_id:
                students = self.env['op.student'].sudo().search([('course_detail_ids.batch_id', '=', session.batch_id.id), ('user_id', '!=', False)])
                u_ids.update(students.mapped('user_id').ids)
            session.user_ids = [(6, 0, list(u_ids))]

    @api.constrains('start_datetime', 'end_datetime')
    def _check_date_time(self):
        for rec in self:
            if rec.start_datetime >= rec.end_datetime:
                raise ValidationError(_('Время окончания должно быть позже начала.'))

    @api.constrains('faculty_id', 'start_datetime', 'end_datetime', 'classroom_id', 'batch_id')
    def _check_conflicts(self):
        for rec in self:
            if rec.state == 'cancel': continue
            domain = [('id', '!=', rec.id), ('state', '!=', 'cancel'), ('start_datetime', '<', rec.end_datetime), ('end_datetime', '>', rec.start_datetime)]
            if self.search_count(domain + [('faculty_id', '=', rec.faculty_id.id)]):
                raise ValidationError(_('Учитель %s занят!') % rec.faculty_id.name)
            if self.search_count(domain + [('batch_id', '=', rec.batch_id.id)]):
                raise ValidationError(_('Группа %s занята!') % rec.batch_id.name)
            if rec.classroom_id and self.search_count(domain + [('classroom_id', '=', rec.classroom_id.id)]):
                raise ValidationError(_('Кабинет %s занят!') % rec.classroom_id.name)

    @api.onchange('start_datetime')
    def _onchange_start_datetime(self):
        if self.start_datetime:
            self.end_datetime = self.start_datetime + timedelta(minutes=40)



    # # --- СИНХРОНИЗАЦИЯ (Timetable -> Attendance) ---
    # def _sync_sheet_state(self, new_state):
    #     """Вспомогательный метод для обновления связанного журнала"""
    #     AttendanceSheet = self.env['op.attendance.sheet'].sudo()
    #     for session in self:
    #         sheet = AttendanceSheet.search([('session_id', '=', session.id)], limit=1)
    #         if sheet and sheet.state != new_state:
    #             # Если переводим в 'done', вызываем метод завершения журнала с расчетами
    #             if new_state == 'done':
    #                 sheet.action_attendance_done()
    #             else:
    #                 sheet.write({'state': new_state})


    # @api.onchange('course_id')
    # def _onchange_course_id(self):
    #     self.batch_id = False
    #     self.subject_id = False
    #     if self.course_id:
    #         return {'domain': {'subject_id': [('id', 'in', self.course_id.subject_ids.ids)]}}



    # def _create_attendance_sheet(self):
    #     """Оптимизированное создание журнала в статусе 'confirm'"""
    #     AttendanceSheet = self.env['op.attendance.sheet']
    #     for record in self:
    #         if AttendanceSheet.search_count([('session_id', '=', record.id)]):
    #             continue
            
    #         students = self.env['op.student'].search([
    #             ('course_detail_ids.course_id', '=', record.course_id.id),
    #             ('course_detail_ids.batch_id', '=', record.batch_id.id),
    #             ('active', '=', True)
    #         ])
    #         register = self.env['op.attendance.register'].search([
    #             ('course_id', '=', record.course_id.id),
    #             ('batch_id', '=', record.batch_id.id)
    #         ], limit=1)
    #         present_type = self.env['op.attendance.type'].search([('present', '=', True)], limit=1)

    #         AttendanceSheet.create({
    #             'session_id': record.id,
    #             'attendance_date': record.start_datetime.date(),
    #             'faculty_id': record.faculty_id.id,
    #             'register_id': register.id if register else False,
    #             'state': 'confirm', # Журнал сразу "Утвержден"
    #             'attendance_line': [(0, 0, {
    #                 'student_id': s.id,
    #                 'attendance_type_id': present_type.id if present_type else False,
    #             }) for s in students]
    #         })

