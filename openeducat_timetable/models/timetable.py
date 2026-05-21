from datetime import timedelta
import datetime
import pytz
from odoo import _, api, fields, models # type: ignore
from odoo.exceptions import ValidationError # type: ignore

class OpSession(models.Model):
    _name = "op.session"
    _inherit = ["mail.thread", "mail.activity.mixin"] 
    _description = "Sessions"
    _order = "start_datetime desc, batch_id, id"

    timetable_date = fields.Date(string='Дата урока', 
        compute='_compute_timetable_date', store=True, index=True)

    days_id = fields.Many2one('op.day', string='День недели', 
        compute='_compute_day_info', store=True, group_expand='_read_group_days')

    @api.depends('start_datetime')
    def _compute_timetable_date(self):
        for rec in self:
            if rec.start_datetime:
                rec.timetable_date = rec.start_datetime.date()
            else:
                rec.timetable_date = False

    @api.model
    def _read_group_days(self, days, domain):
        # Ищем дни через sudo, чтобы избежать проблем с правами
        all_days = self.env['op.day'].sudo().search([])        
        sessions = self.env['op.session'].search(domain)
        
        active_day_ids = sessions.mapped('days_id').ids
        
        # for day in all_days:
        #     # Сравниваем текущее значение, чтобы не дергать базу лишний раз
        #     new_fold_state = (day.id not in active_day_ids)
        #     if day.fold != new_fold_state:
        #         day.sudo().fold = new_fold_state # Пишем через sudo
            
        return all_days
    
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
    timing_id = fields.Many2one('op.timing', string='Lesson Slot')

    @api.onchange('timing_id', 'timetable_date')
    def _onchange_timing(self):
        if self.timing_id and self.timetable_date:
            dt_start = datetime.datetime.combine(self.timetable_date, 
                datetime.time(self.timing_id.lesson_hour, self.timing_id.lesson_minute))
            local_tz = pytz.timezone(self.env.user.tz or 'UTC')
            self.start_datetime = local_tz.localize(dt_start).astimezone(pytz.utc).replace(tzinfo=None)
            dt_end = dt_start + datetime.timedelta(minutes=self.timing_id.duration)
            self.end_datetime = local_tz.localize(dt_end).astimezone(pytz.utc).replace(tzinfo=None)

    name = fields.Char(compute='_compute_name', string='Name', store=False)
    timing = fields.Char(compute='_compute_timing', string='Session Timing', store=False)
    state = fields.Selection([
        ('draft', 'Черновик'), 
        ('confirm', 'Утвержден'),
        ('start', 'Урок идет'),
        ('done', 'Завершен'), 
        ('cancel', 'Отменен')],
        string='Status', default='draft', tracking=True, index=True)

    active = fields.Boolean(default=True)
    color = fields.Integer('Color Index', default=0)
    user_ids = fields.Many2many('res.users', string='Allowed Users', compute='_compute_user_ids', store=True)
    
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

    def lecture_draft(self):
        self.write({'state': 'draft'})

    def lecture_confirm(self):
        self.write({'state': 'confirm'})

    def lecture_start(self):
        self.write({'state': 'start'})

    def lecture_done(self):
        self.write({'state': 'done'})

    def lecture_cancel(self):
        self.write({'state': 'cancel'})

    def lecture_edit(self):
        self.write({'state': 'start'})

    
    @api.depends('start_datetime')
    def _compute_day_info(self):
        # Карта соответствия номеров дней из Python кодам из нашей базы
        day_map = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'}
        for record in self:
            if record.start_datetime:
                day_code = day_map.get(record.start_datetime.weekday())
                # Ищем запись дня в нашей новой модели
                day_rec = self.env['op.day'].search([('code', '=', day_code)], limit=1)
                record.days_id = day_rec
            else:
                record.days_id = False
                
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
