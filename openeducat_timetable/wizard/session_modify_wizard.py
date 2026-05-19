from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time

class SessionModifyLine(models.TransientModel):
    _name = 'session.modify.line'
    _description = 'Строка мастера правок'

    wizard_id = fields.Many2one('session.modify.wizard', string='Мастер')
    is_selected = fields.Boolean('Выбрать', default=False)
    session_id = fields.Many2one('op.session', 'Урок', readonly=True)
    faculty_id = fields.Many2one('op.faculty', 'Учитель', required=True)
    classroom_id = fields.Many2one('op.classroom', 'Кабинет')
    start_datetime = fields.Datetime('Начало', required=True)
    end_datetime = fields.Datetime('Конец', required=True)
    conflict_status = fields.Char('Статус', compute='_compute_conflict')

    @api.onchange('start_datetime')
    def _onchange_start_datetime(self):
        if self.start_datetime and self.session_id:
            clean_start = self.start_datetime.replace(second=0, microsecond=0)
            if self.start_datetime != clean_start:
                self.start_datetime = clean_start
            duration = self.session_id.end_datetime - self.session_id.start_datetime
            self.end_datetime = self.start_datetime + duration

    @api.depends('faculty_id', 'classroom_id', 'start_datetime', 'end_datetime')
    def _compute_conflict(self):
        for rec in self:
            if not rec.session_id:
                rec.conflict_status = "ОК"
                continue
            domain = [
                ('id', '!=', rec.session_id.id),
                ('state', '!=', 'cancel'),
                ('start_datetime', '<', rec.end_datetime),
                ('end_datetime', '>', rec.start_datetime)
            ]
            msg = []
            if self.env['op.session'].search_count(domain + [('faculty_id', '=', rec.faculty_id.id)]):
                msg.append(_("Занят"))
            if rec.classroom_id and self.env['op.session'].search_count(domain + [('classroom_id', '=', rec.classroom_id.id)]):
                msg.append(_("Кабинет занят"))
            rec.conflict_status = ", ".join(msg) if msg else "ОК"


class SessionModifyWizard(models.TransientModel):
    _name = 'session.modify.wizard'
    _description = 'Мастер корректировки учебного процесса'

    # --- ВХОДНЫЕ ДАННЫЕ (Фильтры) ---
    date_from = fields.Date('С даты', required=True, default=fields.Date.today)
    date_to = fields.Date('По дату', required=True, default=fields.Date.today)
    batch_ids = fields.Many2many('op.batch', string='Классы / Группы')
    filter_faculty_id = fields.Many2one('op.faculty', string='Учитель')

    faculty_domain = fields.Char(compute='_compute_faculty_domain')
    swap_domain = fields.Char(compute='_compute_swap_domain')
    date_to_end = fields.Datetime(compute='_compute_date_to_end')

    # --- ХАРАКТЕР ИЗМЕНЕНИЙ (Режим) ---
    action_mode = fields.Selection([
        ('replace', 'ЗАМЕЩЕНИЕ'),
        ('shift', 'ПЕРЕНОС'),
        ('swap', 'РОКИРОВКА')
    ], string='Тип корректировки', default='replace', required=True)

    new_faculty_id = fields.Many2one('op.faculty', string='Новый учитель')
    new_classroom_id = fields.Many2one('op.classroom', string='Новый кабинет')
    target_date = fields.Date('Дата переноса')

    swap_session_a_id = fields.Many2one('op.session', string='Урок А')
    swap_session_b_id = fields.Many2one('op.session', string='Урок Б')

    line_ids = fields.One2many('session.modify.line', 'wizard_id', string='Уроки')
    free_window_info = fields.Text('Доступность', readonly=True)

    @api.depends('date_to')
    def _compute_date_to_end(self):
        for rec in self:
            rec.date_to_end = datetime.combine(rec.date_to, time.max) if rec.date_to else False

    @api.depends('date_from', 'date_to_end')
    def _compute_faculty_domain(self):
        for rec in self:
            if rec.date_from and rec.date_to_end:
                sessions = self.env['op.session'].search([('start_datetime', '>=', rec.date_from), ('start_datetime', '<=', rec.date_to_end), ('state', '!=', 'cancel')])
                rec.faculty_domain = str([('id', 'in', sessions.mapped('faculty_id').ids)])
            else: rec.faculty_domain = str([])

    @api.depends('date_from', 'date_to_end', 'filter_faculty_id', 'batch_ids')
    def _compute_swap_domain(self):
        for rec in self:
            domain = [('state', 'in', ['draft', 'confirm']), ('start_datetime', '>=', rec.date_from), ('start_datetime', '<=', rec.date_to_end)]
            if rec.filter_faculty_id: domain.append(('faculty_id', '=', rec.filter_faculty_id.id))
            if rec.batch_ids: domain.append(('batch_id', 'in', rec.batch_ids.ids))
            rec.swap_domain = str(domain)

    # --- ИНТЕРАКТИВНЫЙ ЦИКЛ РЕЖИМОВ ---
    def action_cycle_mode(self):
        self.ensure_one()
        modes = ['replace', 'shift', 'swap']
        current_index = modes.index(self.action_mode)
        self.action_mode = modes[(current_index + 1) % len(modes)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_search_sessions(self):
        self.ensure_one()
        self.line_ids = [(5, 0, 0)]
        domain = [
            ('start_datetime', '>=', fields.Datetime.to_string(self.date_from)),
            ('start_datetime', '<', fields.Datetime.to_string(self.date_to + timedelta(days=1))),
            ('state', 'in', ['draft', 'confirm', 'start'])
        ]
        if self.batch_ids: domain.append(('batch_id', 'in', self.batch_ids.ids))
        if self.filter_faculty_id: domain.append(('faculty_id', '=', self.filter_faculty_id.id))

        sessions = self.env['op.session'].search(domain, order='start_datetime asc')
        lines = []
        for s in sessions:
            new_start, new_end = s.start_datetime, s.end_datetime
            if self.action_mode == 'shift' and self.target_date:
                delta = self.target_date - s.start_datetime.date()
                new_start += delta
                new_end += delta

            lines.append((0, 0, {
                'session_id': s.id,
                'faculty_id': self.new_faculty_id.id if (self.action_mode == 'replace' and self.new_faculty_id) else s.faculty_id.id,
                'classroom_id': self.new_classroom_id.id if (self.action_mode == 'replace' and self.new_classroom_id) else s.classroom_id.id,
                'start_datetime': new_start,
                'end_datetime': new_end,
                'is_selected': False,
            }))
        self.line_ids = lines
        self._update_free_windows()
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'new',
        }

    def _update_free_windows(self):
        target = self.new_faculty_id or self.filter_faculty_id
        if not target or self.action_mode == 'swap':
            self.free_window_info = ""
            return
        check_date = self.target_date or self.date_from
        sessions = self.env['op.session'].search([('faculty_id', '=', target.id), ('timetable_date', '=', check_date), ('state', '!=', 'cancel')], order='start_datetime asc')
        res = f"Занятость {target.name} на {check_date}:\n"
        if not sessions: res += "— Свободен"
        for s in sessions:
            st = fields.Datetime.context_timestamp(self, s.start_datetime).strftime('%H:%M')
            et = fields.Datetime.context_timestamp(self, s.end_datetime).strftime('%H:%M')
            res += f"• {st}-{et}\n"
        self.free_window_info = res

    def action_apply(self):
        self.ensure_one()
        if self.action_mode == 'swap':
            if not self.swap_session_a_id or not self.swap_session_b_id:
                raise ValidationError(_("Выберите два урока."))
            a, b = self.swap_session_a_id, self.swap_session_b_id
            t_a_s, t_a_e = a.start_datetime, a.end_datetime
            t_b_s, t_b_e = b.start_datetime, b.end_datetime
            a.write({'start_datetime': t_b_s, 'end_datetime': t_b_e})
            b.write({'start_datetime': t_a_s, 'end_datetime': t_a_e})
            for s in [a, b]:
                sheet = self.env['op.attendance.sheet'].sudo().search([('session_id', '=', s.id)], limit=1)
                if sheet: sheet.attendance_date = s.start_datetime.date()
            return {'type': 'ir.actions.client', 'tag': 'reload'}

        selected_lines = self.line_ids.filtered(lambda l: l.is_selected)
        if not selected_lines: raise ValidationError("Выберите хотя бы один урок.")

        for line in selected_lines:
            line.session_id.write({
                'faculty_id': line.faculty_id.id, 'classroom_id': line.classroom_id.id,
                'start_datetime': line.start_datetime, 'end_datetime': line.end_datetime,
            })
            sheet = self.env['op.attendance.sheet'].sudo().search([('session_id', '=', line.session_id.id)], limit=1)
            if sheet: sheet.write({'faculty_id': line.faculty_id.id, 'attendance_date': line.start_datetime.date()})
        return {'type': 'ir.actions.client', 'tag': 'reload'}