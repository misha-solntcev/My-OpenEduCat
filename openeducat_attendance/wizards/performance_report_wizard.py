from odoo import api, fields, models


class PerformanceReportWizard(models.TransientModel):
    _name = 'performance.report.wizard'
    _description = 'Визард сводного отчета успеваемости класса'

    # Селекторы «пустой выбор = всё»: год не выбран — все годы, классы не
    # выбраны — все классы, четверти не выбраны — все четверти года класса
    # (согласовано 10.11.2026, как фильтры визардов «Текущих»/«Итоговых»).
    academic_year_id = fields.Many2one('op.academic.year', string='Учебный год',
        default=lambda self: self._get_default_year())

    batch_ids = fields.Many2many('op.batch', string='Классы')

    term_ids = fields.Many2many('op.academic.term', string='Четверти')

    source = fields.Selection([
        ('final', 'Итоговые оценки'),
        ('current', 'Текущие средние'),
    ], string='Источник ячеек', default='final', required=True,
        help='Итоговые оценки — оценка за четверть из ведомости. '
             'Текущие средние — средний балл текущих оценок за период.')

    hide_empty_subjects = fields.Boolean(
        string='Скрывать предметы без оценок', default=True,
        help='Не показывать предметы, по которым за выбранный период нет ни '
             'одной оценки. Выключите, чтобы увидеть предметы без итогов — '
             '«кто из учителей ещё не сдал».')

    # Служебные поля: списки годов/классов/четвертей для доменов полей
    # (год необязателен, поэтому домен через compute, а не по academic_year_id).
    available_term_ids = fields.Many2many('op.academic.term', string='Четверти выбора',
        compute='_compute_available')
    available_batch_ids = fields.Many2many('op.batch', string='Классы выбора',
        compute='_compute_available')

    @api.depends('academic_year_id')
    def _compute_available(self):
        for rec in self:
            rec.available_term_ids = self.env['op.academic.term'].search([
                ('parent_term', '!=', False),
                ('academic_year_id', 'in', rec.academic_year_id.ids or
                    self.env['op.academic.year'].search([]).ids),
            ], order='term_start_date asc')
            rec.available_batch_ids = rec.env['op.batch'].sudo().search([
                ('start_date', '<=', rec.academic_year_id.end_date),
                ('end_date', '>=', rec.academic_year_id.start_date),
            ], order='sequence') if rec.academic_year_id else \
                rec.env['op.batch'].sudo().search([], order='sequence')

    @api.onchange('academic_year_id')
    def _onchange_academic_year_id(self):
        """Смена/очистка года сбрасывает классы и четверти."""
        self.batch_ids = [(5, 0, 0)]
        self.term_ids = [(5, 0, 0)]

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref(
            'openeducat_attendance.action_report_performance_analysis'
        ).report_action(self)

    def _get_default_year(self):
        today = fields.Date.today()
        year = self.env['op.academic.year'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today)
        ], limit=1)
        return year.id if year else False
