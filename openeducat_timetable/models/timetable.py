from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import datetime
import pytz

class OpDay(models.Model):
    _name = 'op.day'
    _description = 'День недели'
    _order = 'sequence'

    name = fields.Char('Название', required=True, translate=True)
    code = fields.Char('Код', required=True)
    sequence = fields.Integer('Последовательность', default=10)
    fold = fields.Boolean('Свернуть пустые', default=False)


class OpTiming(models.Model):
    _name = "op.timing"
    _description = "Сетка звонков"
    _order = "sequence"

    name = fields.Char('Название', size=32, required=True)
    lesson_hour = fields.Integer('Часы', required=True)
    lesson_minute = fields.Integer('Минуты', required=True)
    duration = fields.Integer('Продолжительность', default=40)
    sequence = fields.Integer('Последовательность', default=10)

    def _compute_display_name(self):
        for rec in self:
            start = f"{rec.lesson_hour:02d}:{rec.lesson_minute:02d}"
            total_min = rec.lesson_hour * 60 + rec.lesson_minute + rec.duration
            h_e, m_e = divmod(total_min, 60)
            rec.display_name = f"{rec.name} ({start} - {int(h_e):02d}:{int(m_e):02d})"


class OpSession(models.Model):
    _name = "op.session"
    _inherit = ["mail.thread", "mail.activity.mixin", "op.time.mixin"]
    _description = "Уроки расписания"
    _order = "timetable_date asc, start_datetime asc"

    # --- ПОЛЯ ДЛЯ XML (Имена и Группировки) ---
    name = fields.Char(string='Name', compute='_compute_name', store=False)
    timing = fields.Char(string='Session Timing', compute='_compute_timing', store=False)
    
    # Это поле Odoo ищет в Pivot view
    faculty_surname = fields.Char(
        string='Учитель (фамилия)', 
        compute='_compute_faculty_surname', 
        store=True)

    # --- ПОЛЯ ВРЕМЕНИ ---
    timetable_date = fields.Date(
        string='Дата урока', required=True, index=True,
        compute='_compute_day_info', store=True, readonly=False)

    days_id = fields.Many2one(
        'op.day', string='День недели',
        compute='_compute_day_info', store=True, group_expand='_read_group_days')

    start_datetime = fields.Datetime(
        'Start Time', required=True, index=True, tracking=True,
        default=fields.Datetime.now)
    
    end_datetime = fields.Datetime(
        'End Time', required=True, index=True, tracking=True)

    # --- СВЯЗИ ---
    faculty_id = fields.Many2one('op.faculty', 'Faculty', required=True, index=True, tracking=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True, index=True, tracking=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, index=True, tracking=True)
    course_id = fields.Many2one('op.course', 'Course', required=True, index=True)
    classroom_id = fields.Many2one('op.classroom', 'Classroom', index=True, tracking=True)
    timing_id = fields.Many2one('op.timing', string='Lesson Slot')
    
    # Вспомогательные поля
    active = fields.Boolean(default=True)
    color = fields.Integer(related='subject_id.color', store=True, readonly=True)
    faculty_subject_ids = fields.Many2many('op.subject', related='faculty_id.faculty_subject_ids')
    user_ids = fields.Many2many('res.users', string='Allowed Users', compute='_compute_user_ids', store=True)

    state = fields.Selection([
        ('draft', 'Черновик'), 
        ('confirm', 'Утвержден'),        
        ('start', 'Урок идет'), 
        ('done', 'Завершен'), 
        ('cancel', 'Отменен')
    ], string='Status', default='draft', tracking=True, index=True)

    # --- ЛОГИКА ВЫЧИСЛЕНИЙ ---

    @api.depends('faculty_id.name')
    def _compute_faculty_surname(self):
        for rec in self:
            if rec.faculty_id and rec.faculty_id.name:                
                rec.faculty_surname = rec.faculty_id.name.split()[0]
            else:
                rec.faculty_surname = ""

    @api.depends('subject_id', 'batch_id', 'faculty_id')
    def _compute_name(self):
        for rec in self:
            subj = rec.subject_id.name or ''
            batch = rec.batch_id.name or ''
            faculty = rec.faculty_id.name.split()[0] if rec.faculty_id.name else ''
            rec.name = f"{subj} - {batch} - {faculty}"

    @api.depends('start_datetime', 'end_datetime')
    def _compute_timing(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                s = rec._convert_to_local(rec.start_datetime).strftime('%H:%M')
                e = rec._convert_to_local(rec.end_datetime).strftime('%H:%M')
                rec.timing = f"{s} - {e}"
            else:
                rec.timing = ""

    @api.depends('start_datetime')
    def _compute_day_info(self):
        for record in self:
            if record.start_datetime:
                local_dt = record._convert_to_local(record.start_datetime)
                record.timetable_date = local_dt.date()
                day_code = local_dt.strftime('%A').lower()
                record.days_id = self.env['op.day'].search([('code', '=', day_code)], limit=1)

    @api.depends('batch_id', 'faculty_id')
    def _compute_user_ids(self):        
        for session in self:
            u_ids = set()
            if session.faculty_id.user_id: u_ids.add(session.faculty_id.user_id.id)
            if session.batch_id:
                students = self.env['op.student'].sudo().search([
                    ('course_detail_ids.batch_id', '=', session.batch_id.id), 
                    ('user_id', '!=', False)])
                u_ids.update(students.mapped('user_id').ids)
            session.user_ids = [(6, 0, list(u_ids))]

    @api.model
    def _read_group_days(self, days, domain):
        return self.env['op.day'].sudo().search([])

    @api.onchange('timing_id', 'timetable_date')
    def _onchange_sync_with_timing(self):
        if self.timing_id and self.timetable_date:
            tz_name = self._get_school_timezone()
            local_tz = pytz.timezone(tz_name)
            naive_start = datetime.datetime.combine(
                self.timetable_date, 
                datetime.time(self.timing_id.lesson_hour, self.timing_id.lesson_minute))
            local_start = local_tz.localize(naive_start)
            self.start_datetime = local_start.astimezone(pytz.utc).replace(tzinfo=None)
            self.end_datetime = (local_start + datetime.timedelta(minutes=self.timing_id.duration)).astimezone(pytz.utc).replace(tzinfo=None)

    @api.constrains('start_datetime', 'end_datetime')
    def _check_date_time(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.start_datetime >= rec.end_datetime:
                raise ValidationError(_('Время окончания должно быть позже начала.'))

    # --- МЕТОДЫ СОСТОЯНИЙ ---
    def lecture_draft(self): self.write({'state': 'draft'})
    def lecture_confirm(self): self.write({'state': 'confirm'})
    def lecture_start(self): self.write({'state': 'start'})
    def lecture_done(self): self.write({'state': 'done'})
    def lecture_cancel(self): self.write({'state': 'cancel'})
    def lecture_edit(self): self.write({'state': 'start'})

    def write(self, vals):
        for rec in self:
            # 1. Если карточку ПЕРЕТАСКИВАЮТ (пришло только время начала)
            if 'start_datetime' in vals and 'timing_id' not in vals:
                sync_data = rec._sync_time_values(start_dt=vals['start_datetime'])
                vals.update(sync_data)

            # 2. Если меняют УРОК или ДАТУ в форме
            # Мы принудительно пересчитываем ВСЕ поля времени, чтобы календарь "проснулся"
            elif 'timing_id' in vals or 'timetable_date' in vals:
                t_id = vals.get('timing_id', rec.timing_id.id)
                d_val = vals.get('timetable_date', rec.timetable_date)
                
                if t_id and d_val:
                    # Получаем полный набор данных от Миксина (start, end, date, slot)
                    sync_data = rec._sync_time_values(timing_id=t_id, date_val=d_val)
                    vals.update(sync_data)

        return super(OpSession, self).write(vals)

    @api.onchange('timing_id', 'timetable_date', 'start_datetime')
    def _onchange_time_sync(self):
        """Двусторонняя связь полей в интерфейсе"""
        # Если пользователь вручную ввел время или дату
        if self.start_datetime:
            # Если изменили именно время начала (ввод руками)
            res = self._sync_time_values(
                start_dt=self.start_datetime,
                timing_id=self.timing_id.id if self.timing_id else False,
                date_val=self.timetable_date
            )
            # Обновляем поля в UI. В Odoo 18 важно использовать update()
            self.update(res)