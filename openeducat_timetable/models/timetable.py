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
        compute='_compute_day_info', store=True, readonly=False,
        precompute=True)

    days_id = fields.Many2one(
        'op.day', string='День недели',
        compute='_compute_days_id', store=True, group_expand='_read_group_days')

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
    academic_year_id = fields.Many2one(
        'op.academic.year', string='Учебный год',
        compute='_compute_academic_year', store=True, index=True)

    # --- FLAGS ---
    active = fields.Boolean(default=True)
    color = fields.Integer(
        string='Цвет карточки',
        compute='_compute_session_color',
        store=True
    )

    user_ids = fields.Many2many('res.users', string='Allowed Users', compute='_compute_user_ids', store=True)

    has_conflict = fields.Boolean(
        "Конфликт", compute='_compute_has_conflict', store=True)

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
            rec.color = 1 if (rec.has_conflict and not rec.conflict_override) else rec.subject_id.color or 0

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
            parts = []
            for s in conflicts:
                if s.faculty_id == rec.faculty_id:
                    parts.append('<li>учитель: <strong>%s</strong> уже ведёт урок</li>' % s.faculty_id.name)
                if s.classroom_id == rec.classroom_id:
                    parts.append('<li>кабинет: <strong>%s</strong> занят</li>' % s.classroom_id.name)
                if s.batch_id == rec.batch_id:
                    parts.append('<li>класс: у <strong>%s</strong> уже есть урок</li>' % s.batch_id.name)
            rec.conflict_details_html = '<ul class="mb-0 ps-3">%s</ul>' % ''.join(parts) if parts else ''


    @api.depends('faculty_id.name')
    def _compute_faculty_surname(self):
        for rec in self:
            if rec.faculty_id and rec.faculty_id.name:
                rec.faculty_surname = rec.faculty_id.name.split()[0]
            else:
                rec.faculty_surname = ""

    @api.depends('subject_id', 'batch_id', 'faculty_surname')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.subject_id.name or ''} - {rec.batch_id.name or ''} - {rec.faculty_surname or ''}"

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

    @api.depends('timetable_date')
    def _compute_days_id(self):
        """День недели из timetable_date (не из start_datetime!).
        Отдельный compute: если days_id висит на _compute_day_info вместе
        с timetable_date и в create передан только timetable_date, Odoo
        помечает общий compute выполненным и days_id остаётся NULL
        (баг 176 пустых уроков сентября 2026)."""
        day_map = {d.code: d.id for d in self.env['op.day'].sudo().search([])}
        for record in self:
            if record.timetable_date:
                record.days_id = day_map.get(
                    record.timetable_date.strftime('%A').lower())

    @api.depends('timetable_date')
    def _compute_academic_year(self):
        """Учебный год = диапазон [start_date, end_date], в который попадает
        timetable_date. Диапазоны годов не пересекаются."""
        years = self.env['op.academic.year'].sudo().search([])
        spans = [(y.start_date, y.end_date, y.id) for y in years]
        for record in self:
            d = record.timetable_date
            record.academic_year_id = next(
                (yid for start, end, yid in spans if start <= d <= end), False)

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
    # WRITE / CREATE — sync conflict flags of intersecting sessions
    # ---------------------------------------------------------------

    def _conflict_neighbor_ids(self):
        """Ids of other sessions intersecting any of these records."""
        ids = set()
        for rec in self:
            if rec.id:
                ids.update(rec._find_overlapping_sessions().ids)
        return list(ids)

    def _recompute_conflict_flags(self):
        """Recalculate stored has_conflict/color on this recordset.
        Needed for *neighbors*: a stored compute only triggers on the
        record whose own fields changed, but moving session A also
        changes whether session B has a conflict.

        Работает под sudo: пишет только служебные флаговые поля
        (has_conflict/color, отсечены _FLAG_ONLY в write), но соседом
        может оказаться ЧУЖОЙ урок — teacher_session_write_rule
        («учитель пишет только свои сессии») иначе роняет операцию
        юзера AccessError'ом (кейс Ермаковой, 2026-09-10)."""
        sudo_self = self.sudo()
        for rec in sudo_self:
            rec._compute_has_conflict()
        for rec in sudo_self:
            rec._compute_session_color()
        self.env['op.session'].flush_model(['has_conflict', 'color',
                                            'conflict_override'])

    def write(self, vals):
        """Override: snap time to grid + drop conflict override only
        when the conflict persists after the move."""
        if any(f in vals for f in ('start_datetime', 'timing_id', 'timetable_date')):
            for rec in self:
                sync = rec._sync_time_values(
                    start_dt=vals.get('start_datetime'),
                    timing_id=vals.get('timing_id'),
                    date_val=vals.get('timetable_date'),
                )
                if sync:
                    vals.update(sync)
        _RESET_FIELDS = {
            'start_datetime', 'end_datetime',
            'faculty_id', 'batch_id', 'classroom_id',
            'timing_id', 'timetable_date',
        }
        # Auto-reset is deferred: the override survives the move if the
        # session lands in a free slot (e.g. drag away and drag back).
        # Writes that carry only conflict-flag fields (from our own
        # _recompute_conflict_flags) must skip this logic entirely,
        # otherwise flag compute -> write -> compute recursion.
        _FLAG_ONLY = {'has_conflict', 'color', 'conflict_override'}
        if _FLAG_ONLY.issuperset(vals):
            return super(OpSession, self).write(vals)
        auto_reset = (vals.get('conflict_override') is None
                      and _RESET_FIELDS.intersection(vals))
        if auto_reset:
            vals.pop('conflict_override', None)
        # ГЕЙТ: пересечения могут измениться только при смене «геометрии»
        # урока (время/слот/дата/учитель/класс/кабинет) или при уходе в/
        # выходе из cancel (cancel исключён из поиска пересечений).
        # Обычный write({'state': 'confirm/start/done'}) с кнопок журнала
        # соседей не трогает вовсе — раньше пересчёт флагов соседей гонялся
        # на каждом write и ронял учителя AccessError'ом на чужом уроке
        # (кейс Ермаковой, 2026-09-10), плюс давал два лишних SQL-поиска
        # на каждое проведение.
        is_cancel_transition = (
            'state' in vals
            and bool({'draft', 'cancel'}
                     & ({vals['state']} | set(self.mapped('state')))))
        if not (_RESET_FIELDS.intersection(vals) or is_cancel_transition):
            return super(OpSession, self).write(vals)
        # Neighbors BEFORE the move: sessions that intersected the old
        # time/resources — they may stop conflicting once we move.
        pre_neighbors = self.browse(self._conflict_neighbor_ids())
        res = super(OpSession, self).write(vals)
        # Neighbors AFTER the move: new intersections.
        post_neighbors = self.browse(self._conflict_neighbor_ids())
        (self | pre_neighbors | post_neighbors)._recompute_conflict_flags()
        if auto_reset:
            # Reset approval only where a conflict still exists.
            self.filtered(lambda r: r.has_conflict).write(
                {'conflict_override': False})
            (self | pre_neighbors | post_neighbors)._recompute_conflict_flags()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        sessions = super(OpSession, self).create(vals_list)
        # New session may put neighbors into conflict.
        (sessions | sessions.browse(
            sessions._conflict_neighbor_ids()))._recompute_conflict_flags()
        return sessions

    def unlink(self):
        # Neighbors before deletion: their conflict may disappear with us.
        pre_neighbors = self.browse(self._conflict_neighbor_ids())
        res = super(OpSession, self).unlink()
        pre_neighbors._recompute_conflict_flags()
        return res

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
                # Build per-resource conflict lines (single pass)
                conflict_lines = []
                for s in blocking:
                    if prevent_faculty and s.faculty_id == rec.faculty_id:
                        conflict_lines.append(
                            "- учитель: %s уже ведёт урок в это время"
                            % rec.faculty_id.name)
                    if prevent_classroom and s.classroom_id == rec.classroom_id:
                        conflict_lines.append(
                            "- кабинет: %s занят"
                            % rec.classroom_id.name)
                    if prevent_batch and s.batch_id == rec.batch_id:
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
        if not (self.start_datetime and self.end_datetime):
            return self.env['op.session']
        domain = [
            ('id', '!=', self._origin.id or self.id),
            ('state', '!=', 'cancel'),
            ('start_datetime', '<', self.end_datetime),
            ('end_datetime', '>', self.start_datetime),
        ]
        resources = []
        for field_name in ('faculty_id', 'batch_id', 'classroom_id'):
            if self[field_name]:
                resources.append((field_name, '=', self[field_name].id))
        if not resources:
            return self.env['op.session']
        or_prefix = ['|'] * (len(resources) - 1)
        return self.search(domain + or_prefix + resources)

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
