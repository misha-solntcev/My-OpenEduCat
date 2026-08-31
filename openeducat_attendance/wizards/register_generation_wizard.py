from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AttendanceRegisterGenerationWizard(models.TransientModel):
    """Мастер генерации настроек журналов (op.attendance.register).

    Создаёт регистры посещаемости по связке «класс × четверть» для выбранного
    учебного года. Четверти берутся из op.academic.term (дети-семестры с
    parent_term). Существующие регистры не дублируются (сопоставление по
    course_id + batch_id + четверти в имени).
    """
    _name = "attendance.register.generation.wizard"
    _description = "Генерация настроек журналов (регистров по четвертям)"

    academic_year_id = fields.Many2one(
        'op.academic.year', string='Учебный год', required=True,
        default=lambda self: self._default_academic_year())
    batch_ids = fields.Many2many(
        'op.batch', string='Классы',
        help='Классы, для которых будут созданы регистры по четвертям. '
             'Пусто = все классы с уроками в выбранном учебном году.')
    preview = fields.Html(string='Предпросмотр', compute='_compute_preview')

    @api.model
    def _default_academic_year(self):
        """Текущий год: тот, в чей диапазон попадает сегодня."""
        today = fields.Date.context_today(self)
        return self.env['op.academic.year'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today),
        ], limit=1)

    @api.model
    def _batches_for_year(self, year):
        """Все активные классы. Не привязываемся к урокам: расписание может
        быть сгенерировано позже регистров."""
        return self.env['op.batch'].sudo().search([])

    @api.model
    def _quarter_terms(self, year):
        """Четверти года: термы-дети (parent_term != False).
        Отсекаем термы, не принадлежащие году, по датам семестров-родителей."""
        return self.env['op.academic.term'].search([
            ('parent_term', '!=', False),
            ('academic_year_id', '=', year.id),
        ]).sorted('term_start_date')

    def _plan(self):
        """План: [(batch, term)] по которому будут создаваться регистры."""
        self.ensure_one()
        year = self.academic_year_id
        # В onchange batch_ids содержит виртуальные записи (NewId):
        # берём _origin, чтобы работали сортировка по id и поиск регистров.
        batches = (self.batch_ids._origin or self._batches_for_year(year))
        terms = self._quarter_terms(year)
        Register = self.env['op.attendance.register'].sudo()

        existing = {
            (r.batch_id.id, term.name)
            for r in Register.search([('batch_id', 'in', batches.ids)])
            for term in terms
            if r.name and r.name.startswith(term.name)
        }
        plan = []
        for batch in batches.sorted('id'):
            for idx, term in enumerate(terms, start=1):
                if (batch.id, term.name) in existing:
                    continue
                plan.append((batch, term, idx,
                             "%s - %s" % (term.name, batch.name)))
        return batches, terms, plan

    @api.depends('academic_year_id', 'batch_ids')
    def _compute_preview(self):
        for wiz in self:
            if not wiz.academic_year_id:
                wiz.preview = '<p>Выберите учебный год.</p>'
                continue
            batches, terms, plan = wiz._plan()
            lines = [
                "<li>Класс <b>%s</b> — %s</li>" % (batch.name, term.name)
                for batch, term, idx, name in plan
            ]
            wiz.preview = (
                "<p>Классов: <b>%s</b>, четвертей: <b>%s</b>. "
                "Будет создано регистров: <b>%s</b> (существующие пропускаются).</p>"
                "<ul>%s</ul>"
                % (len(batches), len(terms), len(plan), ''.join(lines)))

    def _make_code(self, batch, idx):
        """Уникальный код ≤16 символов: <класс><№ четверти>[суффикс]."""
        Register = self.env['op.attendance.register'].sudo()
        base = (batch.name or 'B%d' % batch.id).replace(' ', '')[:13]
        code = "%s%dч" % (base, idx)
        if Register.search([('code', '=', code)], limit=1):
            code = ("REG-%s-%d" % (batch.id, idx))[:16]
            if Register.search([('code', '=', code)], limit=1):
                raise UserError(_(
                    "Не удалось подобрать уникальный код регистра для "
                    "класса %s (четверть %s)." % (batch.name, idx)))
        return code

    def action_generate(self):
        self.ensure_one()
        batches, terms, plan = self._plan()
        if not terms:
            raise UserError(_(
                "У учебного года «%s» нет четвертей (op.academic.term с "
                "заполненным родительским семестром). Сначала настройте "
                "семестры и четверти.") % self.academic_year_id.name)
        if not plan:
            raise UserError(_(
                "Все регистры для выбранных классов уже существуют. "
                "Ничего создавать не нужно."))
        # Диалог подтверждения перед записью
        return {
            'type': 'ir.actions.act_window',
            'name': 'Подтвердите создание',
            'res_model': 'attendance.register.generation.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'plan_ready': True},
        }

    def action_confirm_generate(self):
        self.ensure_one()
        batches, terms, plan = self._plan()
        if not plan:
            raise UserError(_("План создания пуст."))
        Register = self.env['op.attendance.register'].sudo()
        vals_list = [{
            'name': name,
            'code': self._make_code(batch, idx),
            'course_id': batch.course_id.id,
            'batch_id': batch.id,
        } for batch, term, idx, name in plan]
        registers = Register.create(vals_list)
        summary = "Создано регистров: %s" % len(registers)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Готово',
                'message': summary,
                'sticky': False,
            },
        }
