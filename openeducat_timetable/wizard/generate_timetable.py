from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from collections import Counter, defaultdict
import datetime


class GenerateSession(models.TransientModel):
    _name = "generate.time.table"
    _description = "Generate Sessions"
    _rec_name = "batch_id"
    _inherit = ['op.time.mixin']

    batch_id = fields.Many2one('op.batch', 'Класс', required=True,
        help='Класс, для которого создаётся расписание.')

    start_date = fields.Date('Дата начала генерации', required=True, default=fields.Date.context_today)
    end_date = fields.Date('Дата окончания генерации', required=True,
        default=lambda self: self._default_end_date())
    # Селектор периода (четверть/семестр из op.academic.term). Пусто =
    # «вручную»: даты редактируются свободно, селектор только подставляет.
    term_id = fields.Many2one('op.academic.term', 'Период',
        domain="[('academic_year_id', '=', current_year_id)]")
    # Обычное поле с default (НЕ computed): non-stored computed без полевых
    # зависимостей не попадает в payload первого onchange — домен term_id
    # оставался пустым до первого любого onchange.
    current_year_id = fields.Many2one('op.academic.year',
        default=lambda self: self._default_current_year())

    import_start_date = fields.Date('Начало периода импорта')
    import_end_date = fields.Date('Конец периода импорта')
    source_batch_id = fields.Many2one(
        'op.batch', 'Копировать из класса',
        help='Класс, чьё расписание копируется кнопкой «Импорт». '
             'Пусто = импорт невозможен.')
    show_import = fields.Boolean('Показать импорт', default=False)

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

    @api.model
    def _default_end_date(self):
        """Конец текущего семестра; если сегодня не накрыт ни одним
        семестром — конец месяца (прежнее поведение)."""
        today = fields.Date.context_today(self)
        Term = self.env['op.academic.term']
        term = Term.search([
            ('term_start_date', '<=', today),
            ('term_end_date', '>=', today),
        ], order='term_start_date desc', limit=1)
        if term:
            return term.term_end_date
        return (today + datetime.timedelta(days=30)).replace(day=1) \
            - datetime.timedelta(days=1)

    @api.model
    def _default_current_year(self):
        today = fields.Date.context_today(self)
        return self.env['op.academic.year'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today),
        ], limit=1).id

    @api.onchange('term_id')
    def _onchange_term_id(self):
        if self.term_id:
            self.start_date = self.term_id.term_start_date
            self.end_date = self.term_id.term_end_date

    @api.onchange('start_date', 'end_date')
    def _onchange_dates_manual(self):
        """Ручная правка дат сбрасывает селектор периода — он не должен
        показывать терм, которому даты уже не соответствуют."""
        if self.term_id and (
                self.start_date != self.term_id.term_start_date
                or self.end_date != self.term_id.term_end_date):
            self.term_id = False

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
        """Предрасчёт сводки и переход к шагу подтверждения."""
        self.ensure_one()
        if not self.time_table_lines:
            raise ValidationError("Таблица расписания не заполнена.")
        target_batch = self.batch_id
        target_course = target_batch.course_id

        # Собираем новые уроки (день недели x строки мастера)
        sessions_data = []
        curr_date = self.start_date
        while curr_date <= self.end_date:
            weekday = str(curr_date.weekday())
            day_lines = self.time_table_lines.filtered(lambda l: l.day == weekday)
            for line in day_lines:
                sync = self._sync_time_values(date_val=curr_date, timing_id=line.timing_id.id)
                if sync:
                    sessions_data.append({
                        'course_id': target_course.id,
                        'batch_id': target_batch.id,
                        'faculty_id': line.faculty_id.id,
                        'subject_id': line.subject_id.id,
                        'classroom_id': line.classroom_id.id,
                        'timing_id': line.timing_id.id,
                        'start_datetime': sync['start_datetime'],
                        'end_datetime': sync['end_datetime'],
                        'timetable_date': sync['timetable_date'],
                        # display-ключи для списка учительских пересечений
                        'timing_name': line.timing_id.name,
                        'subject_name': line.subject_id.name,
                        'faculty_name': line.faculty_id.name,
                    })
            curr_date += datetime.timedelta(days=1)

        if not sessions_data:
            raise ValidationError("Нет данных для генерации.")

        # Существующие уроки параллели за период
        Session = self.env['op.session']
        existing = Session.search([
            ('batch_id', '=', target_batch.id),
            ('state', '!=', 'cancel'),
            ('timetable_date', '>=', self.start_date),
            ('timetable_date', '<=', self.end_date),
        ])
        new_slots = {(d['timetable_date'], d['timing_id']) for d in sessions_data}
        overlaps = existing.filtered(
            lambda s: (s.timetable_date, s.timing_id.id) in new_slots)
        # Журналы посещаемости — опциональный спутник: при прогоне тестов
        # модуль openeducat_attendance может быть ещё не загружен в реестре
        # (порядок загрузки модулей при -u нестабилен), поэтому страж.
        protected = self.env['op.session']
        if 'op.attendance.sheet' in self.env:
            protected = self.env['op.attendance.sheet'].sudo().search(
                [('session_id', 'in', existing.ids)]).mapped('session_id')

        # Параллельные уроки ВНУТРИ самой генерации (импорт приносит два
        # предмета на один звонок — «Английский А/Б»): существующих уроков
        # в периоде может не быть вовсе, а конфликты уже есть. Без учёта
        # этих пар шаг подтверждения молчит (has_soft_conflicts=False),
        # галочка автоутверждения не показывается, и вся пара создаётся
        # красной. Считаем уроки, попавшие в слоты с несколькими уроками
        # (пара даёт 2 — при auto_approve утверждается ОБЕ карточки).
        slot_load = Counter((d['timetable_date'], d['timing_id'])
                            for d in sessions_data)
        stat_parallel = sum(n for n in slot_load.values() if n > 1)

        # Единый список всех «совпадений» для диалога (по всем случаям):
        # 1) параллельные уроки в одном слоте (new↔new, «Английский А/Б»);
        # 2) новые уроки на слотах с ЗАЩИЩЁННЫМИ уроками (new↔журнал:
        #    урок уже прошёл, журнал заполнен — старый не удалится,
        #    будет задвоение; именно этот случай путает завуча);
        # 3) учительские пересечения (new↔урок другого класса: «физра —
        #    два класса вместе»).
        day_short = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')

        def _when(d):
            return '%s %s, %s' % (d['timetable_date'].strftime('%d.%m'),
                                  day_short[d['timetable_date'].weekday()],
                                  d['timing_name'])

        min_start = min(d['start_datetime'] for d in sessions_data)
        max_end = max(d['end_datetime'] for d in sessions_data)

        # 1. Параллельные внутри генерации
        slot_groups = defaultdict(list)
        for i, d in enumerate(sessions_data):
            slot_groups[(d['timetable_date'], d['timing_id'])].append(i)
        rows_parallel = []
        for (date_, timing_id_), idxs in sorted(slot_groups.items()):
            if len(idxs) < 2:
                continue
            subjects = ' ↔ '.join(sessions_data[i]['subject_name']
                                  for i in idxs)
            teachers = ' / '.join(sorted(
                {sessions_data[i]['faculty_name'] for i in idxs}))
            rows_parallel.append(
                "<tr><td>%s %s, %s</td><td>%s</td><td>%s</td></tr>"
                % (date_.strftime('%d.%m'), day_short[date_.weekday()],
                   sessions_data[idxs[0]]['timing_name'], subjects, teachers))

        # 2. Новые уроки на слотах с защищёнными журналами
        protected_by_slot = defaultdict(list)
        for s in protected:
            protected_by_slot[(s.timetable_date, s.timing_id.id)].append(s)
        stat_protected_overlap = 0
        seen_prot = set()
        rows_protected = []
        for d in sessions_data:
            prots = protected_by_slot.get((d['timetable_date'],
                                           d['timing_id']))
            if not prots:
                continue
            # точный дубль защищённого урока (тот же предмет и учитель)
            # не создаётся вовсе — в списке задвоений его не пугаем
            exact = [s for s in prots
                     if s.subject_id.id == d['subject_id']
                     and s.faculty_id.id == d['faculty_id']]
            if exact:
                continue
            stat_protected_overlap += 1
            for s in prots:
                key = (d['timetable_date'], d['timing_id'], s.id)
                if key in seen_prot:
                    continue
                seen_prot.add(key)
                rows_protected.append(
                    "<tr><td>%s</td><td>%s (%s)</td><td>%s (%s) — журнал "
                    "заполнен, не удаляется</td></tr>"
                    % (_when(d), d['subject_name'], d['faculty_name'],
                       s.subject_id.name, s.faculty_id.name))

        # 3. Учительские пересечения с другими классами
        others = Session.search([
            ('state', '!=', 'cancel'),
            ('batch_id', '!=', target_batch.id),
            ('start_datetime', '<', max_end),
            ('end_datetime', '>', min_start),
        ])
        stat_faculty = 0
        rows_faculty = []
        seen_fac_pairs = set()
        for d in sessions_data:
            hits = others.filtered(
                lambda s: s.faculty_id.id == d['faculty_id']
                and s.start_datetime < d['end_datetime']
                and s.end_datetime > d['start_datetime'])
            if not hits:
                continue
            stat_faculty += 1
            when = _when(d)
            for s in hits:
                key = (d['timetable_date'], d['timing_id'], s.id)
                if key in seen_fac_pairs:
                    continue
                seen_fac_pairs.add(key)
                rows_faculty.append(
                    "<tr><td>%s</td><td>%s</td><td>%s (%s)</td>"
                    "<td>%s (%s)</td></tr>"
                    % (d['faculty_name'], when, d['subject_name'],
                       target_batch.name, s.subject_id.name, s.batch_id.name))

        sections = []
        if rows_parallel:
            sections.append(
                "<div class='mb-1'><b>Параллельные уроки в одном слоте:</b>"
                "<table class='table table-sm table-bordered mb-2'>"
                "<tr class='table-warning'><th>Когда</th><th>Предметы</th>"
                "<th>Учителя</th></tr>%s</table></div>"
                % ''.join(rows_parallel))
        if rows_protected:
            sections.append(
                "<div class='mb-1'><b>Новые уроки на слотах с защищёнными "
                "журналами (будет задвоение):</b><table class='table "
                "table-sm table-bordered mb-2'>"
                "<tr class='table-warning'><th>Когда</th><th>Новый урок</th>"
                "<th>Защищённый урок</th></tr>%s</table></div>"
                % ''.join(rows_protected))
        if rows_faculty:
            sections.append(
                "<div class='mb-1'><b>Учительские пересечения:</b>"
                "<table class='table table-sm table-bordered mb-2'>"
                "<tr class='table-warning'><th>Учитель</th><th>Когда</th>"
                "<th>Новый урок</th><th>Пересекается с</th></tr>%s</table></div>"
                % ''.join(rows_faculty))
        conflicts_html = ''.join(sections) or False

        confirm = self.env['generate.time.table.confirm'].create({
            'gen_wizard_id': self.id,
            'mode': 'overlap' if overlaps else 'add',
            'stat_new': len(sessions_data),
            'stat_existing': len(existing),
            'stat_overlap': len(overlaps),
            'stat_protected': len(protected),
            'stat_parallel': stat_parallel,
            'stat_protected_overlap': stat_protected_overlap,
            'stat_faculty': stat_faculty,
            'conflicts_html': conflicts_html,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'generate.time.table.confirm',
            'res_id': confirm.id,
            'view_mode': 'form',
            'target': 'new',
        }

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
        if not self.source_batch_id:
            raise ValidationError(
                "Укажите класс-источник: из какого класса копировать расписание.")
        if not (self.import_start_date and self.import_end_date):
            raise ValidationError("Выберите даты для импорта.")

        sessions = self.env['op.session'].search([
            ('batch_id', '=', self.source_batch_id.id),
            ('timetable_date', '>=', self.import_start_date),
            ('timetable_date', '<=', self.import_end_date),
            ('state', '!=', 'cancel'),
            ('timing_id', '!=', False),
        ], order='timetable_date desc')

        if not sessions:
            raise ValidationError("Уроков для импорта не найдено.")

        # Дедупликация. Ключ = день + слот + предмет + учитель: параллельные
        # уроки («Английский А»/«Английский Б» на одном звонке) попадают в
        # таблицу КАК ОТДЕЛЬНЫЕ строки — их разводит конфликт-механика
        # генерации (красная карточка / conflict_override в шаге
        # подтверждения). Отсекаются только полные дубли: период импорта
        # длиннее недели, и один и тот же урок повторяется в каждой неделе
        # периода. Раньше ключ был (день, слот) — второй урок пары молча
        # терялся без всякого предупреждения.
        seen = set()
        lines_data = []
        skipped_dups = 0
        for s in sessions:
            day = str(s.timetable_date.weekday())
            key = (day, s.timing_id.id, s.subject_id.id, s.faculty_id.id)
            if key in seen:
                skipped_dups += 1
                continue
            seen.add(key)
            lines_data.append((0, 0, {
                'day': day, 'timing_id': s.timing_id.id, 'faculty_id': s.faculty_id.id,
                'subject_id': s.subject_id.id, 'classroom_id': s.classroom_id.id,
            }))

        self.time_table_lines.unlink()
        self.write({'time_table_lines': lines_data})

        # Слоты, на которые импорт положил несколько уроков (параллельные
        # подгруппы) — сразу виден масштаб будущих «конфликтов».
        import_load = Counter((d['day'], d['timing_id'])
                              for _, _, d in lines_data)
        parallel_slots = sum(1 for n in import_load.values() if n > 1)

        # Отчёт вместо тихого успеха. params.next поддерживается
        # обработчиком display_notification (web/client_actions.js) —
        # переоткрывает мастера, чтобы таблица отрисовала новые строки.
        # ВАЖНО: next возвращается из КЛИЕНТСКОГО действия напрямую в
        # doAction, минуя серверный clean_action/generate_views — без
        # явного views падает в _preprocessAction (action.views.map).
        reopen = self._reopen_wizard()
        reopen['views'] = [[False, 'form']]
        if skipped_dups:
            message = (
                "Импортировано уроков: %s. Пропущено полных дублей: %s "
                "(тот же предмет и учитель на том же уроке — повтор в "
                "неделях периода импорта)."
                % (len(lines_data), skipped_dups))
            ntype = 'warning'
        else:
            message = "Импортировано уроков: %s." % len(lines_data)
            ntype = 'success'
        if parallel_slots:
            message += " Слотов с параллельными уроками: %s." % parallel_slots
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Импорт расписания',
                'message': message,
                'type': ntype,
                'sticky': False,
                'next': reopen,
            },
        }

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

    @api.onchange('classroom_id')
    def _onchange_classroom_id(self):
        for rec in self:
            if rec.gen_time_table.batch_id:
                classroom = self.env['op.classroom'].search([
                    ('batch_id', '=', rec.gen_time_table.batch_id.id)
                ], limit=1)
                if classroom:
                    rec.classroom_id = classroom.id
