from odoo import models, fields, api

class CurrentGradesReportWizard(models.TransientModel):
    _name = 'current.grades.report.wizard'
    _description = 'Визард отчета текущих оценок'

    academic_year_id = fields.Many2one('op.academic.year', string='Учебный год', required=True,
        default=lambda self: self._get_default_year())
    
    term_ids = fields.Many2many('op.academic.term', string='Четверть',
        domain="[('academic_year_id', '=', academic_year_id), ('parent_term', '!=', False)]")
    
    batch_ids = fields.Many2many('op.batch', string='Класс')
    
    student_ids = fields.Many2many('op.student', string='Ученик')
    
    subject_ids = fields.Many2many('op.subject', string='Предмет')

    def _get_default_year(self):
        return self.env['op.academic.year'].search([
            ('start_date', '<=', fields.Date.today()),
            ('end_date', '>=', fields.Date.today())
        ], limit=1).id

    @api.onchange('batch_ids')
    def _onchange_batch_ids(self):
        self.student_ids = [(5, 0, 0)]

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('openeducat_attendance.action_report_current_grades').report_action(self)