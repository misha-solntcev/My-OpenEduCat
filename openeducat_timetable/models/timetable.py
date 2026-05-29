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
    color = fields.Integer(
        string='Цвет карточки', 
        compute='_compute_session_color', 
        store=True
    )

    faculty_subject_ids = fields.Many2many('op.subject', related='faculty_id.faculty_subject_ids')
    user_ids = fields.Many2many('res.users', string='Allowed Users', compute='_compute_user_ids', store=True)

    allow_overlap = fields.Boolean("Разрешить наложение", default=False, tracking=True)
    has_conflict = fields.Boolean("Конфликт", compute='_compute_conflict_data', store=True)    

    state = fields.Selection([
        ('draft', 'Черновик'), 
        ('confirm', 'Утвержден'),        
        ('start', 'Урок идет'), 
        ('done', 'Завершен'), 
        ('cancel', 'Отменен')
    ], string='Status', default='draft', tracking=True, index=True)

    # --- ЛОГИКА ВЫЧИСЛЕНИЙ ---

    @api.depends('has_conflict', 'allow_overlap', 'subject_id.color')
    def _compute_session_color(self):
        for rec in self:
            # 1. Сначала проверяем: есть ли неразрешенный конфликт?
            if rec.has_conflict and not rec.allow_overlap:
                rec.color = 1  # Принудительно КРАСНЫЙ (индекс 1 в Odoo)
            else:
                # 2. Если конфликта нет (или он разрешен), 
                # читаем тот самый настроенный цвет из предмета
                # Это то же самое, что делал related, но теперь через наш код
                rec.color = rec.subject_id.color or 0

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
    
    # --- МЕТОДЫ СОСТОЯНИЙ ---
    def lecture_draft(self): self.write({'state': 'draft'})
    def lecture_confirm(self): self.write({'state': 'confirm'})
    def lecture_start(self): self.write({'state': 'start'})
    def lecture_done(self): self.write({'state': 'done'})
    def lecture_cancel(self): self.write({'state': 'cancel'})
    def lecture_edit(self): self.write({'state': 'start'})

    def write(self, vals):        
        if any(f in vals for f in ('start_datetime', 'timing_id', 'timetable_date')):
            for rec in self:
                vals.update(rec._sync_time_values(
                    start_dt=vals.get('start_datetime'),
                    timing_id=vals.get('timing_id'),
                    date_val=vals.get('timetable_date')
                ))
                
        res = super(OpSession, self).write(vals)
        
        if not self._context.get('skip_refresh'):
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'notification', {
                'type': 'refresh',
                'model': self._name,
            })
        return res

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
    

    @api.depends('start_datetime', 'end_datetime', 'faculty_id', 'batch_id', 'classroom_id', 'state')
    def _compute_conflict_data(self):
        """Вычисляет наличие конфликта для базы данных"""
        for rec in self:
            if rec.state == 'cancel' or not rec.start_datetime or not rec.end_datetime:
                rec.has_conflict = False
                continue           
            
            conflicts = rec._get_conflict_list(ignore_settings=True)
            rec.has_conflict = bool(conflicts)

    @api.onchange('start_datetime', 'end_datetime', 'faculty_id', 'batch_id', 'classroom_id')
    def _onchange_check_conflicts_ui(self):
        """Принудительное обновление флага конфликта для интерфейса"""
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                # Ищем любые наложения (игнорируя настройки блокировки)
                conflicts = rec._get_conflict_list(ignore_settings=True)
                rec.has_conflict = bool(conflicts)
            else:
                rec.has_conflict = False

    def _get_conflict_list(self, ignore_settings=False):
        self.ensure_one()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        
        # Если ignore_settings=True, ищем всё (для красного цвета)
        # Если False, ищем только то, что заблокировано в настройках
        check_f = True if ignore_settings else get_param('timetable.is_faculty_constraint') == 'True'
        check_b = True if ignore_settings else get_param('timetable.is_batch_constraint') == 'True'
        check_c = True if ignore_settings else get_param('timetable.is_classroom_constraint') == 'True'

        domain = [
            ('id', '!=', self._origin.id or self.id),
            ('state', '!=', 'cancel'),
            ('start_datetime', '<', self.end_datetime),
            ('end_datetime', '>', self.start_datetime),
        ]
        
        conflicts = []
        def fmt_msg(s):
            st = s._convert_to_local(s.start_datetime).strftime('%H:%M')
            return f"   • {s.subject_id.name} ({s.batch_id.name}) в {st}, каб. {s.classroom_id.name or '?'}"

        if check_f and self.faculty_id:
            res = self.search(domain + [('faculty_id', '=', self.faculty_id.id)])
            if res:
                conflicts.append(_("УЧИТЕЛЬ %s:") % self.faculty_id.name)
                conflicts.extend([fmt_msg(s) for s in res])
        
        if check_b and self.batch_id:
            res = self.search(domain + [('batch_id', '=', self.batch_id.id)])
            if res:
                conflicts.append(_("ГРУППА %s:") % self.batch_id.name)
                conflicts.extend([fmt_msg(s) for s in res])

        if check_c and self.classroom_id:
            res = self.search(domain + [('classroom_id', '=', self.classroom_id.id)])
            if res:
                conflicts.append(_("КАБИНЕТ %s:") % self.classroom_id.name)
                conflicts.extend([fmt_msg(s) for s in res])
        return conflicts

    @api.constrains('faculty_id', 'batch_id', 'classroom_id', 'start_datetime', 'end_datetime', 'state', 'allow_overlap')
    def _check_all_session_constraints(self):
        for rec in self:
            if rec.state == 'cancel' or not rec.start_datetime or not rec.end_datetime:
                continue

            if rec.start_datetime >= rec.end_datetime:
                raise ValidationError(_("Время окончания не может быть раньше начала!"))

            # Проверка блокировки
            conflicts = rec._get_conflict_list(ignore_settings=False)
            if conflicts and not rec.allow_overlap:
                header = _("🛑 БЛОКИРОВКА: КОНФЛИКТ РЕСУРСОВ\n\n")
                raise ValidationError(header + "\n".join(conflicts) + 
                    _("\n\nДля подтверждения наложения включите 'Разрешить наложение' в форме урока."))
            
            # Лог в чат
            all_actual = rec._get_conflict_list(ignore_settings=True)
            if all_actual and not rec._context.get('skip_message_post'):
                rec.message_post(body=_("<b>Внимание:</b> Урок сохранен с наложением на:<br/>%s") % "<br/>".join(all_actual))