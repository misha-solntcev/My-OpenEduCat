from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GenerateTimeTableConfirm(models.TransientModel):
    _name = "generate.time.table.confirm"
    _description = "Подтверждение генерации расписания"

    gen_wizard_id = fields.Many2one(
        'generate.time.table', required=True, ondelete='cascade')
    mode = fields.Selection([
        ('add', 'Добавить уроки'),
        ('overlap', 'Заменить совпадающие'),
        ('all', 'Перезаписать весь период'),
    ], default='add', required=True)

    # --- Предрасчитанная сводка (заполняется при открытии) ---
    stat_new = fields.Integer('Будет создано')
    stat_existing = fields.Integer('Существует в периоде')
    stat_overlap = fields.Integer('Совпадают с новыми')
    stat_protected = fields.Integer('Защищены журналом посещаемости')
    protected_info = fields.Text('Защищённые уроки')

    can_overlap = fields.Boolean(compute='_compute_mode_availability')
    can_all = fields.Boolean(compute='_compute_mode_availability')
    empty_period = fields.Boolean(compute='_compute_mode_availability')
    summary_html = fields.Html(compute='_compute_summary_html')

    @api.depends('stat_existing', 'stat_overlap')
    def _compute_mode_availability(self):
        for rec in self:
            rec.can_overlap = rec.stat_overlap > 0
            rec.can_all = rec.stat_existing > 0
            rec.empty_period = rec.stat_existing == 0
            if not rec.can_overlap and rec.mode == 'overlap':
                rec.mode = 'add'

    @api.depends('stat_new', 'stat_existing', 'stat_overlap',
                 'stat_protected', 'empty_period', 'mode')
    def _compute_summary_html(self):
        for rec in self:
            p = rec.gen_wizard_id.start_date
            e = rec.gen_wizard_id.end_date
            period = "%s – %s" % (p.strftime('%d.%m.%Y'), e.strftime('%d.%m.%Y')) \
                if p and e else ''
            rows = []
            rows.append("<div class='mb-2'>Новых уроков будет создано: "
                        "<b>%s</b></div>" % rec.stat_new)
            if rec.empty_period:
                rows.append(
                    "<div class='alert alert-info py-2 px-3 mb-1'>"
                    "Расписание класса на период %s свободно.</div>" % period)
                rec.summary_html = "".join(rows)
                continue
            rows.append(
                "<div class='mb-1'>Уроков уже существует в периоде %s: "
                "<b>%s</b></div>"
                "<table class='table table-sm table-bordered mb-2'>"
                "<tr><td>Совпадают с новыми (день и время)</td><td><b>%s</b></td></tr>"
                "<tr><td>Не совпадают</td><td><b>%s</b></td></tr>"
                "<tr class='table-warning'><td>Защищены журналом посещаемости "
                "(не удаляются)</td><td><b>%s</b></td></tr>"
                "</table>" % (period, rec.stat_existing, rec.stat_overlap,
                              rec.stat_existing - rec.stat_overlap,
                              rec.stat_protected))
            # Динамический прогноз по выбранному режиму
            protected = min(rec.stat_protected, rec.stat_overlap) \
                if rec.mode == 'overlap' else \
                min(rec.stat_protected, rec.stat_existing)
            if rec.mode == 'add':
                rows.append(
                    "<div class='alert alert-info py-2 px-3 mb-1'>"
                    "При применении: существующие уроки <b>не изменятся</b>, "
                    "добавится <b>%s</b> новых. Если новый урок попадёт на "
                    "занятый слот — будет ошибка.</div>" % rec.stat_new)
            elif rec.mode == 'overlap':
                rows.append(
                    "<div class='alert alert-info py-2 px-3 mb-1'>"
                    "При применении: заменено будет <b>%s</b> совпадающих "
                    "уроков (минус %s защищённых журналом). Остальные %s "
                    "<b>останутся как есть</b>.</div>"
                    % (rec.stat_overlap, protected,
                       rec.stat_existing - rec.stat_overlap))
            else:
                will_delete = max(rec.stat_existing - protected, 0)
                rows.append(
                    "<div class='alert alert-info py-2 px-3 mb-1'>"
                    "При применении: удалено будет <b>%s</b> из %s существующих "
                    "(защищённые журналом пропущены), создано <b>%s</b> новых."
                    "</div>" % (will_delete, rec.stat_existing, rec.stat_new))
            if (rec.mode == 'all'
                    and rec.stat_new < rec.stat_existing - rec.stat_protected):
                rows.append(
                    "<div class='alert alert-warning py-2 px-3 mb-1 small'>"
                    "⚠ Внимание: будет удалено больше уроков, чем создано. "
                    "Дни, не заполненные в таблице мастера, опустеют.</div>")
            rec.summary_html = "".join(rows)

    def action_back(self):
        """Вернуться к таблице мастера."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'generate.time.table',
            'res_id': self.gen_wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply(self):
        self.ensure_one()
        if self.mode == 'overlap' and not self.can_overlap:
            self.mode = 'add'
        if self.mode == 'all' and not self.can_all:
            raise ValidationError("В периоде нет уроков для перезаписи.")
        wizard = self.gen_wizard_id
        if not wizard.time_table_lines:
            raise ValidationError("Таблица расписания не заполнена.")
        target_batch = wizard.target_batch_id or wizard.batch_id
        target_course = target_batch.course_id

        # 1. Собрать новые уроки (тот же движок, что и раньше)
        sessions_data = []
        curr_date = wizard.start_date
        while curr_date <= wizard.end_date:
            weekday = str(curr_date.weekday())
            day_lines = wizard.time_table_lines.filtered(
                lambda l: l.day == weekday)
            for line in day_lines:
                sync = wizard._sync_time_values(
                    date_val=curr_date, timing_id=line.timing_id.id)
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
                    })
            curr_date += timedelta(days=1)

        if not sessions_data:
            raise ValidationError("Нет данных для генерации.")

        Session = self.env['op.session']
        Sheet = self.env['op.attendance.sheet'].sudo()

        # 2. Существующие уроки параллели за период
        existing = Session.search([
            ('batch_id', '=', target_batch.id),
            ('state', '!=', 'cancel'),
            ('timetable_date', '>=', wizard.start_date),
            ('timetable_date', '<=', wizard.end_date),
        ])
        protected = Sheet.search([('session_id', 'in', existing.ids)]).mapped(
            'session_id')

        # 3. Удаление по выбранному режиму
        to_delete = Session.browse()
        if self.mode == 'overlap':
            new_slots = {(d['timetable_date'], d['timing_id'])
                         for d in sessions_data}
            to_delete = existing.filtered(
                lambda s: (s.timetable_date, s.timing_id.id) in new_slots)
        elif self.mode == 'all':
            to_delete = existing
        to_delete = to_delete - protected
        to_delete.unlink()

        # 4. Контроль занятости слотов (после удаления)
        remaining = Session.search([
            ('batch_id', '=', target_batch.id),
            ('state', '!=', 'cancel'),
            ('timetable_date', '>=', wizard.start_date),
            ('timetable_date', '<=', wizard.end_date),
        ])
        occupied = defaultdict(list)
        for sess in remaining:
            occupied[(sess.timetable_date, sess.timing_id.id)].append(sess)
        for d in sessions_data:
            hits = occupied.get((d['timetable_date'], d['timing_id']))
            if hits:
                raise ValidationError(
                    "Слот уже занят: %s, %s — там стоит урок «%s». "
                    "Выберите «Заменить совпадающие» или освободите слот."
                    % (d['timetable_date'].strftime('%d.%m.%Y'),
                       hits[0].timing_id.name or '',
                       hits[0].subject_id.name or ''))

        # 5. Конфликт-чекер учителей/кабинетов
        get_param = self.env['ir.config_parameter'].sudo().get_param
        allow_f = get_param('timetable.allow_faculty_overlap', 'True') == 'True'
        allow_b = get_param('timetable.allow_batch_overlap', 'True') == 'True'
        allow_c = get_param('timetable.allow_classroom_overlap', 'True') == 'True'
        wizard._check_batch_conflicts(sessions_data, allow_f, allow_c, allow_b)

        # 6. Создание
        Session.create(sessions_data)
        return {'type': 'ir.actions.act_window_close'}
