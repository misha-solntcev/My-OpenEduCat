from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from collections import defaultdict
import datetime


class GenerateSession(models.TransientModel):
    _name = "generate.time.table"
    _description = "Generate Sessions"
    _rec_name = "course_id"

    course_id = fields.Many2one('op.course', 'Класс', required=True)
    batch_id = fields.Many2one('op.batch', 'Параллель', required=True)

    start_date = fields.Date('Дата начала генерации', required=True, default=fields.Date.context_today)
    end_date = fields.Date('Дата окончания генерации', required=True,
        default=lambda self: (fields.Date.context_today(self) + datetime.timedelta(days=30)).replace(day=1) - datetime.timedelta(days=1))

    import_start_date = fields.Date('Начало периода импорта')
    import_end_date = fields.Date('Конец периода импорта')

    time_table_lines = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines')
    time_table_lines_1 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '0')])
    time_table_lines_2 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '1')])
    time_table_lines_3 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '2')])
    time_table_lines_4 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '3')])
    time_table_lines_5 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '4')])
    time_table_lines_6 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '5')])
    time_table_lines_7 = fields.One2many('gen.time.table.line', 'gen_time_table', domain=[('day', '=', '6')])

    show_stats = fields.Boolean('Показать статистику', default=False)
    subject_stats_info = fields.Html('Статистика нагрузки', compute='_compute_all_stats')
    faculty_stats_info = fields.Html('Нагрузка учителей', compute='_compute_all_stats')

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date:
            next_month = self.start_date.replace(day=28) + datetime.timedelta(days=4)
            self.end_date = next_month.replace(day=1) - datetime.timedelta(days=1)

    @api.onchange('course_id')
    def _onchange_course_id(self):
        if self.course_id:
            batches = self.env['op.batch'].search([('course_id', '=', self.course_id.id)])
            self.batch_id = batches[0].id if len(batches) == 1 else False

    @api.onchange('batch_id')
    def _onchange_batch_id(self):
        if self.batch_id:
            classroom = self.env['op.classroom'].search([('batch_id', '=', self.batch_id.id)], limit=1)
            if classroom:
                for f_name, f_obj in self._fields.items():
                    if f_obj.type == 'one2many' and f_obj.comodel_name == 'gen.time.table.line':
                        lines = self[f_name]
                        if lines:
                            lines.write({'classroom_id': classroom.id})

    # --- BULK CONFLICT VALIDATION (before create) ---

    def _check_batch_conflicts(self, sessions_data, allow_faculty, allow_classroom, allow_batch):
        """Validate batch data before touching the DB.

        1) In-memory check among sessions_data themselves.
        2) One DB query against existing sessions.

        Raises ValidationError if a blocking conflict is found,
        so that no records are created at all.
        """
        if not sessions_data:
            return

        fac_intervals = []
        bat_intervals = []
        cls_intervals = []

        for d in sessions_data:
            s = d['start_datetime']
            e = d['end_datetime']
            if d.get('faculty_id'):
                fac_intervals.append((d['faculty_id'], s, e))
            if d.get('batch_id'):
                bat_intervals.append((d['batch_id'], s, e))
            if d.get('classroom_id'):
                cls_intervals.append((d['classroom_id'], s, e))

        def _overlaps(intervals):
            for i in range(len(intervals)):
                for j in range(i + 1, len(intervals)):
                    rid_i, si, ei = intervals[i]
                    rid_j, sj, ej = intervals[j]
                    if rid_i and rid_j and rid_i == rid_j and si < ej and sj < ei:
                        return (intervals[i], intervals[j])
            return None

        if not allow_faculty:
            hit = _overlaps(fac_intervals)
            if hit:
                fac_name = self.env['op.faculty'].browse(hit[0][0]).name or '?'
                raise ValidationError(
                    "🛑 БЛОКИРОВКА: конфликт учителя внутри генерируемых данных.\n"
                    "Учитель %s назначен на два урока одновременно.\n"
                    "Отключите контроль совмещения в настройках или "
                    "исправьте расписание." % fac_name)
        if not allow_batch:
            hit = _overlaps(bat_intervals)
            if hit:
                raise ValidationError(
                    "🛑 БЛОКИРОВКА: конфликт класса внутри генерируемых данных.")
        if not allow_classroom:
            hit = _overlaps(cls_intervals)
            if hit:
                raise ValidationError(
                    "🛑 БЛОКИРОВКА: конфликт кабинета внутри генерируемых данных.")

        # DB check: one query for existing sessions in the date range
        min_start = min(d['start_datetime'] for d in sessions_data)
        max_end = max(d['end_datetime'] for d in sessions_data)

        db_domain = [
            ('state', '!=', 'cancel'),
            ('start_datetime', '<', max_end),
            ('end_datetime', '>', min_start),
        ]
        existing = self.env['op.session'].search(db_domain)
        if not existing:
            return

        def _conflicts_with_db(intervals, resource_field):
            for rid, s, e in intervals:
                if not rid:
                    continue
                for sess in existing:
                    rec = getattr(sess, resource_field)
                    if rec and rec.id == rid and sess.start_datetime < e and sess.end_datetime > s:
                        return True
            return False

        if not allow_faculty and _conflicts_with_db(fac_intervals, 'faculty_id'):
            raise ValidationError(
                "🛑 БЛОКИРОВКА: конфликт учителя с уже существующими уроками.")
        if not allow_batch and _conflicts_with_db(bat_intervals, 'batch_id'):
            raise ValidationError(
                "🛑 БЛОКИРОВКА: конфликт класса с уже существующими уроками.")
        if not allow_classroom and _conflicts_with_db(cls_intervals, 'classroom_id'):
            raise ValidationError(
                "🛑 БЛОКИРОВКА: конфликт кабинета с уже существующими уроками.")

    # --- MAIN GENERATION ENGINE ---

    def act_gen_time_table(self):
        self.ensure_one()
        if not self.time_table_lines:
            raise ValidationError("Таблица расписания не заполнена.")

        # 1. No existing sessions for this batch in the period
        existing_count = self.env['op.session'].search_count([
            ('batch_id', '=', self.batch_id.id),
            ('timetable_date', '>=', self.start_date),
            ('timetable_date', '<=', self.end_date),
            ('state', '!=', 'cancel'),
        ])
        if existing_count > 0:
            raise ValidationError(
                "Для этого класса уже создано %s уроков. Сначала удалите их." % existing_count)

        # 2. Build sessions_data
        sessions_data = []
        curr_date = self.start_date
        while curr_date <= self.end_date:
            weekday = str(curr_date.weekday())
            day_lines = self.time_table_lines.filtered(lambda l: l.day == weekday)
            for line in day_lines:
                sync = self._sync_time_values(date_val=curr_date, timing_id=line.timing_id.id)
                if sync:
                    sessions_data.append({
                        'course_id': self.course_id.id,
                        'batch_id': self.batch_id.id,
                        'faculty_id': line.faculty_id.id,
                        'subject_id': line.subject_id.id,
                        'classroom_id': line.classroom_id.id,
                        'timing_id': line.timing_id.id,
                        'start_datetime': sync['start_datetime'],
                        'end_datetime': sync['end_datetime'],
                        'timetable_date': sync['timetable_date'],
                    })
            curr_date += datetime.timedelta(days=1)

        if not sessions_data:
            raise ValidationError("Нет данных для генерации.")

        # 3. Validate conflicts BEFORE touching DB
        get_param = self.env['ir.config_parameter'].sudo().get_param
        allow_f = get_param('timetable.allow_faculty_overlap', 'True') == 'True'
        allow_b = get_param('timetable.allow_batch_overlap', 'True') == 'True'
        allow_c = get_param('timetable.allow_classroom_overlap', 'True') == 'True'
        self._check_batch_conflicts(sessions_data, allow_f, allow_c, allow_b)

        # 4. Bulk create (constrains act as safety net)
        self.env['op.session'].create(sessions_data)
        return {'type': 'ir.actions.act_window_close'}

    # --- STATISTICS ---

    @api.depends('show_stats', 'time_table_lines_1', 'time_table_lines_2', 'time_table_lines_3',
                 'time_table_lines_4', 'time_table_lines_5', 'time_table_lines_6', 'time_table_lines_7')
    def _compute_all_stats(self):
        for rec in self:
            if not rec.show_stats:
                rec.subject_stats_info = rec.faculty_stats_info = False
                continue

            lines = rec.time_table_lines

            subj_data = defaultdict(int)
            fac_data = defaultdict(int)
            for l in lines:
                if l.subject_id:
                    subj_data[l.subject_id] += 1
                if l.faculty_id:
                    fac_data[l.faculty_id.name] += 1

            s_res = ['<div class="d-flex flex-wrap gap-2 ps-2" style="font-size: 15px;"><b>📚 Предметы:</b>']
            for subj, count in sorted(subj_data.items(), key=lambda x: x[0].sequence):
                s_res.append('<span class="badge rounded-pill o_tag o_tag_subtle o_tag_color_%s border px-2 py-1">%s: %s</span>' % (subj.color, subj.name, count))
            rec.subject_stats_info = "".join(s_res) + "</div>"

            f_res = ['<div class="d-flex flex-wrap gap-2 ps-2 mt-2" style="font-size: 15px;"><b>👨‍🏫 Учителя:</b>']
            for name, count in sorted(fac_data.items()):
                bg = "background: #dc3545; color: white;" if count > 30 else "background: #f8f9fa; border: 1px solid #ddd;"
                f_res.append('<span class="badge rounded-pill px-2 py-1" style="%s">%s: %s</span>' % (bg, name, count))
            rec.faculty_stats_info = "".join(f_res) + "</div>"

    def action_toggle_stats(self):
        self.show_stats = not self.show_stats
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('time_table_lines_1', 'time_table_lines_2', 'time_table_lines_3',
                  'time_table_lines_4', 'time_table_lines_5', 'time_table_lines_6', 'time_table_lines_7')
    def _onchange_refresh_stats(self):
        self._compute_all_stats()

    def action_clear_all(self):
        self.time_table_lines.unlink()
        return self._reopen_wizard()

    def action_clear_day(self):
        day = self.env.context.get('day_to_clear')
        if day is not None:
            self.time_table_lines.filtered(lambda l: l.day == str(day)).unlink()
        return self._reopen_wizard()

    def _reopen_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_import_last_week(self):
        self.ensure_one()
        if not (self.import_start_date and self.import_end_date):
            raise ValidationError("Выберите даты для импорта.")

        sessions = self.env['op.session'].search([
            ('batch_id', '=', self.batch_id.id),
            ('timetable_date', '>=', self.import_start_date),
            ('timetable_date', '<=', self.import_end_date),
            ('state', '!=', 'cancel'),
            ('timing_id', '!=', False),
        ], order='timetable_date desc')

        if not sessions:
            raise ValidationError("Уроков для импорта не найдено.")

        seen = set()
        lines_data = []
        for s in sessions:
            day = str(s.timetable_date.weekday())
            if (day, s.timing_id.id) in seen:
                continue
            seen.add((day, s.timing_id.id))
            lines_data.append((0, 0, {
                'day': day, 'timing_id': s.timing_id.id, 'faculty_id': s.faculty_id.id,
                'subject_id': s.subject_id.id, 'classroom_id': s.classroom_id.id,
            }))

        self.time_table_lines.unlink()
        self.write({'time_table_lines': lines_data})
        return self._reopen_wizard()

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Дата окончания периода не может быть раньше даты начала.")


class GenerateSessionLine(models.TransientModel):
    _name = 'gen.time.table.line'
    _description = 'Generate Time Table Lines'
    _rec_name = 'timing_id'

    gen_time_table = fields.Many2one('generate.time.table', 'Time Table', required=True)
    faculty_id = fields.Many2one('op.faculty', 'Учитель', required=True)
    subject_id = fields.Many2one('op.subject', 'Предмет', required=True,
        domain="[('id', 'in', faculty_subject_ids)]")
    faculty_subject_ids = fields.Many2many('op.subject', related='faculty_id.faculty_subject_ids')
    timing_id = fields.Many2one('op.timing', 'Урок', required=True)
    classroom_id = fields.Many2one('op.classroom', 'Кабинет')
    day = fields.Selection([
        ('0', 'Понедельник'),
        ('1', 'Вторник'),
        ('2', 'Среда'),
        ('3', 'Четверг'),
        ('4', 'Пятница'),
        ('5', 'Суббота'),
        ('6', 'Воскресенье'),
    ], 'День', required=True)

    @api.onchange('faculty_id')
    def _onchange_faculty_id(self):
        if self.gen_time_table.batch_id and not self.classroom_id:
            classroom = self.env['op.classroom'].search([('batch_id', '=', self.gen_time_table.batch_id.id)], limit=1)
            if classroom:
                self.classroom_id = classroom.id

        if self.faculty_id and self.faculty_id.faculty_subject_ids:
            if len(self.faculty_id.faculty_subject_ids) == 1:
                self.subject_id = self.faculty_id.faculty_subject_ids[0].id

    @api.onchange('timing_id')
    def _onchange_timing_id_filter(self):
        if self.day:
            day_field = 'time_table_lines_%s' % (int(self.day) + 1)
            used_timing_ids = self.gen_time_table[day_field].mapped('timing_id').ids
            current_id = self.timing_id.id or (self._origin.timing_id.id if hasattr(self, '_origin') else False)
            other_used_ids = [tid for tid in used_timing_ids if tid != current_id]
            return {'domain': {'timing_id': [('id', 'not in', other_used_ids)]}}

    @api.onchange('gen_time_table.batch_id')
    def _onchange_classroom_id(self):
        for rec in self:
            if rec.gen_time_table.batch_id:
                classroom = self.env['op.classroom'].search([
                    ('batch_id', '=', rec.gen_time_table.batch_id.id)
                ], limit=1)
                if classroom:
                    rec.classroom_id = classroom.id
