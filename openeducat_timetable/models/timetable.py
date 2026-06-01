from odoo import _, api, fields, models
from odoo.exceptions import UserError
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

    # --- DISPLAY FIELDS ---
    name = fields.Char(string='Name', compute='_compute_name', store=False)
    timing = fields.Char(string='Session Timing', compute='_compute_timing', store=False)

    faculty_surname = fields.Char(
        string='Учитель (фамилия)',
        compute='_compute_faculty_surname',
        store=True)

    # --- TIME FIELDS ---
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

    # --- RELATIONS ---
    faculty_id = fields.Many2one('op.faculty', 'Faculty', required=True, index=True, tracking=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True, index=True, tracking=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True, index=True, tracking=True)
    course_id = fields.Many2one('op.course', 'Course', required=True, index=True)
    classroom_id = fields.Many2one('op.classroom', 'Classroom', index=True, tracking=True)
    timing_id = fields.Many2one('op.timing', string='Lesson Slot')

    # --- FLAGS ---
    active = fields.Boolean(default=True)
    color = fields.Integer(
        string='Цвет карточки',
        compute='_compute_session_color',
        store=True
    )

    faculty_subject_ids = fields.Many2many('op.subject', related='faculty_id.faculty_subject_ids')
    user_ids = fields.Many2many('res.users', string='Allowed Users', compute='_compute_user_ids', store=True)

    has_conflict = fields.Boolean(
        "Конфликт", compute='_compute_has_conflict', store=False)

    conflict_override = fields.Boolean(
        string="Конфликт утверждён",
        default=False,
        tracking=True,
        help="Отметьте, если наложение уроков является осознанным выбором "
             "и не является ошибкой. Карточка перестанет быть красной.",
    )

    conflict_details_html = fields.Html(
        string="Детали конфликта",
        compute='_compute_conflict_details_html',
        store=False,
    )

    state = fields.Selection([
        ('draft', 'Черновик'),
        ('confirm', 'Утвержден'),
        ('start', 'Урок идет'),
        ('done', 'Завершен'),
        ('cancel', 'Отменен')
    ], string='Status', default='draft', tracking=True, index=True)

    # ---------------------------------------------------------------
    # COMPUTE METHODS
    # ---------------------------------------------------------------

    @api.depends('has_conflict', 'subject_id.color', 'conflict_override')
    def _compute_session_color(self):
        for rec in self:
            if rec.has_conflict and not rec.conflict_override:
                rec.color = 1  # red
            else:
                rec.color = rec.subject_id.color or 0

    @api.depends('start_datetime', 'end_datetime', 'faculty_id',
                 'batch_id', 'classroom_id', 'state')
    def _compute_has_conflict(self):
        for rec in self:
            if rec.state == 'cancel' or not rec.start_datetime or not rec.end_datetime:
                rec.has_conflict = False
                continue
            conflicts = rec._find_overlapping_sessions()
            rec.has_conflict = bool(conflicts)

    @api.depends('has_conflict', 'faculty_id', 'batch_id', 'classroom_id',
                 'start_datetime', 'end_datetime')
    def _compute_conflict_details_html(self):
        """Build HTML list of conflicting resources for the banner."""
        for rec in self:
            if not rec.has_conflict:
                rec.conflict_details_html = ''
                continue
            conflicts = rec._find_overlapping_sessions()
            items = []
            if rec.faculty_id and conflicts.filtered(
                    lambda s: s.faculty_id == rec.faculty_id):
                items.append(
                    '<li>учитель: <strong>%s</strong> уже ведёт урок в это время</li>'
                    % rec.faculty_id.name)
            if rec.classroom_id and conflicts.filtered(
                    lambda s: s.classroom_id == rec.classroom_id):
                items.append(
                    '<li>кабинет: <strong>%s</strong> занят</li>'
                    % rec.classroom_id.name)
            if rec.batch_id and conflicts.filtered(
                    lambda s: s.batch_id == rec.batch_id):
                items.append(
                    '<li>класс: у <strong>%s</strong> класса уже есть урок в это время</li>'
                    % rec.batch_id.name)
            rec.conflict_details_html = (
                '<ul class="mb-0 ps-3">%s</ul>' % ''.join(items)
            ) if items else ''

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
                record.days_id = self.env['op.day'].search(
                    [('code', '=', day_code)], limit=1)

    @api.depends('batch_id', 'faculty_id')
    def _compute_user_ids(self):
        for session in self:
            u_ids = set()
            if session.faculty_id.user_id:
                u_ids.add(session.faculty_id.user_id.id)
            if session.batch_id:
                students = self.env['op.student'].sudo().search([
                    ('course_detail_ids.batch_id', '=', session.batch_id.id),
                    ('user_id', '!=', False)])
                u_ids.update(students.mapped('user_id').ids)
            session.user_ids = [(6, 0, list(u_ids))]

    @api.model
    def _read_group_days(self, days, domain):
        return self.env['op.day'].sudo().search([])

    # ---------------------------------------------------------------
    # ONCHANGE — time sync (form UI only)
    # ---------------------------------------------------------------

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
            self.end_datetime = (local_start + datetime.timedelta(
                minutes=self.timing_id.duration)).astimezone(pytz.utc).replace(tzinfo=None)

    @api.onchange('timing_id', 'timetable_date', 'start_datetime')
    def _onchange_time_sync(self):
        if self.start_datetime:
            res = self._sync_time_values(
                start_dt=self.start_datetime,
                timing_id=self.timing_id.id if self.timing_id else False,
                date_val=self.timetable_date
            )
            self.update(res)

    @api.onchange('start_datetime', 'end_datetime', 'faculty_id',
                  'batch_id', 'classroom_id')
    def _onchange_show_conflict_hint(self):
        self.ensure_one()
        if not (self.start_datetime and self.end_datetime):
            return
        conflicts = self._find_overlapping_sessions()
        if conflicts:
            names = ", ".join(conflicts.mapped('display_name'))
            return {
                'warning': {
                    'title': _('Конфликт расписания'),
                    'message': _(
                        'Обнаружено пересечение с: %s\n\n'
                        'Если совмещение данного ресурса запрещено '
                        'в настройках — сохранение будет заблокировано.'
                    ) % names,
                },
            }

    # ---------------------------------------------------------------
    # WRITE — snap time to nearest grid slot
    # ---------------------------------------------------------------

    def write(self, vals):
        """Override: snap time to grid + reset conflict override
        when conflict-relevant fields change."""
        if any(f in vals for f in ('start_datetime', 'timing_id', 'timetable_date')):
            for rec in self:
                sync = rec._sync_time_values(
                    start_dt=vals.get('start_datetime'),
                    timing_id=vals.get('timing_id'),
                    date_val=vals.get('timetable_date'),
                )
                if sync:
                    vals.update(sync)
        # Reset conflict_override if time or resources changed
        # (unless user is explicitly setting it to True right now)
        _RESET_FIELDS = {
            'start_datetime', 'end_datetime',
            'faculty_id', 'batch_id', 'classroom_id',
            'timing_id', 'timetable_date',
        }
        if vals.get('conflict_override') is not True and _RESET_FIELDS.intersection(vals):
            vals['conflict_override'] = False
        return super(OpSession, self).write(vals)

    # ---------------------------------------------------------------
    # CONSTRAINS — blocking validation
    # ---------------------------------------------------------------

    @api.constrains('faculty_id', 'batch_id', 'classroom_id',
                    'start_datetime', 'end_datetime', 'state')
    def _check_hard_conflicts(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # prevent_* = True means overlap is FORBIDDEN (blocking mode)
        # When param is missing from DB, Odoo deleted it (False was saved) → overlap allowed
        prevent_faculty = get_param('timetable.prevent_faculty_overlap') == 'True'
        prevent_classroom = get_param('timetable.prevent_classroom_overlap') == 'True'
        prevent_batch = get_param('timetable.prevent_batch_overlap') == 'True'

        for rec in self:
            if rec.state == 'cancel' or not rec.start_datetime or not rec.end_datetime:
                continue

            if rec.start_datetime >= rec.end_datetime:
                raise UserError(
                    "Время окончания не может быть раньше или равно времени начала!")

            conflicts = rec._find_overlapping_sessions()
            if not conflicts:
                continue

            blocking = self.env['op.session']
            if prevent_faculty and rec.faculty_id:
                blocking |= conflicts.filtered(
                    lambda s: s.faculty_id.id == rec.faculty_id.id)
            if prevent_classroom and rec.classroom_id:
                blocking |= conflicts.filtered(
                    lambda s: s.classroom_id.id == rec.classroom_id.id)
            if prevent_batch and rec.batch_id:
                blocking |= conflicts.filtered(
                    lambda s: s.batch_id.id == rec.batch_id.id)

            if blocking:
                # Build per-resource conflict lines
                conflict_lines = []
                if prevent_faculty and rec.faculty_id and blocking.filtered(lambda s: s.faculty_id.id == rec.faculty_id.id):
                    conflict_lines.append(
                        "- учитель: %s уже ведёт урок в это время"
                        % rec.faculty_id.name)
                if prevent_classroom and rec.classroom_id and blocking.filtered(lambda s: s.classroom_id.id == rec.classroom_id.id):
                    conflict_lines.append(
                        "- кабинет: %s занят"
                        % rec.classroom_id.name)
                if prevent_batch and rec.batch_id and blocking.filtered(lambda s: s.batch_id.id == rec.batch_id.id):
                    conflict_lines.append(
                        "- класс: у %s класса уже есть урок в это время"
                        % rec.batch_id.name)
                conflict_body = "\n".join(conflict_lines)

                raise UserError(
                    "🛑 Совмещение запрещено настройками\n\n"
                    "Обнаружен конфликт ресурсов:\n"
                    "%s\n\n"
                    "Снять запрет можно в настройках  (Настройки → Расписание)."
                    % (conflict_body,)
                )

    # ---------------------------------------------------------------
    # PRIVATE HELPERS
    # ---------------------------------------------------------------

    def _find_overlapping_sessions(self):
        self.ensure_one()
        if not self.start_datetime or not self.end_datetime:
            return self.env['op.session']

        domain = [
            ('id', '!=', self._origin.id or self.id),
            ('state', '!=', 'cancel'),
            ('start_datetime', '<', self.end_datetime),
            ('end_datetime', '>', self.start_datetime),
        ]
        resource_filters = []
        if self.faculty_id:
            resource_filters.append(('faculty_id', '=', self.faculty_id.id))
        if self.batch_id:
            resource_filters.append(('batch_id', '=', self.batch_id.id))
        if self.classroom_id:
            resource_filters.append(('classroom_id', '=', self.classroom_id.id))

        if not resource_filters:
            return self.env['op.session']

        if len(resource_filters) == 1:
            full_domain = domain + resource_filters
        else:
            or_prefix = ['|'] * (len(resource_filters) - 1)
            full_domain = domain + or_prefix + resource_filters

        return self.search(full_domain)

    # ---------------------------------------------------------------
    # ACTIONS (state machine)
    # ---------------------------------------------------------------

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
