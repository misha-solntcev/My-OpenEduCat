from odoo import models, fields, api

class StudentReportWizard(models.TransientModel):
    _name = 'student.report.wizard'
    _description = 'Визард итогового отчета'

    batch_ids = fields.Many2many('op.batch', string='Классы')
    academic_year_id = fields.Many2one('op.academic.year',
        string='Учебный год', required=True,
        default=lambda self: self._get_default_academic_year())
    student_ids = fields.Many2many('op.student', string='Ученики')
    # Скрывать предметы, по которым нет ни одной итоговой оценки.
    # Нужно два режима: на 1-м этапе (учитель проверяет, кто не проставил)
    # пустые строки видны; в финальной версии отчёта (для родителей/печати)
    # лишние пустые строки мешают.
    hide_empty_subjects = fields.Boolean(
        string='Скрывать предметы без оценок',
        default=False,
        help='Не показывать предметы, по которым у ученика нет ни одной '
             'итоговой оценки. Выключите на первом этапе — тогда видно, '
             'кто из учителей ещё не проставил итоги.')
    # Служебное поле: классы выбранного учебного года. Батч живёт один год,
    # поэтому в списке есть и «5 А 2025/2026», и «5 А 2026/2027» — без
    # фильтра по году отчёт печатал оба года. Используется в домене поля
    # «Классы» (в view: invisible), чтобы в визарде нельзя было выбрать
    # класс чужого года.
    available_batch_ids = fields.Many2many('op.batch', string='Классы года',
        compute='_compute_available_batch_ids')

    @api.depends('academic_year_id')
    def _compute_available_batch_ids(self):
        for rec in self:
            rec.available_batch_ids = rec._get_year_batches()

    def _get_year_batches(self):
        """Батчи, относящиеся к выбранному учебному году (пересечение дат).

        sudo: поле служебное — по нему строится домен в визарде, и список
        классов должен быть одинаковым для всех, кто открывает форму.
        """
        year = self.academic_year_id
        if not year:
            return self.env['op.batch'].browse()
        return self.env['op.batch'].sudo().search([
            ('start_date', '<=', year.end_date),
            ('end_date', '>=', year.start_date),
        ], order='sequence')

    @api.onchange('academic_year_id')
    def _onchange_academic_year_id(self):
        """Смена года сбрасывает классы и учеников: они от другого года."""
        self.batch_ids = [(5, 0, 0)]
        self.student_ids = [(5, 0, 0)]

    @api.onchange('batch_ids')
    def _onchange_batch_ids(self):
        """Очищаем список выбранных учеников при смене класса"""
        self.student_ids = [(5, 0, 0)]

    def action_print_report(self):
        self.ensure_one()
        # Возвращаем действие отчета, передавая self (запись визарда)
        return self.env.ref('openeducat_attendance.action_student_summary_report').report_action(self)

    def _get_default_academic_year(self):
        today = fields.Date.today()
        year = self.env['op.academic.year'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today)
        ], limit=1)
        return year.id if year else False
