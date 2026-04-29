from odoo import models, fields, api

class StudentReportWizard(models.TransientModel):
    _name = 'student.report.wizard'
    _description = 'Визард итогового отчета'

    batch_id = fields.Many2one('op.batch', string='Класс')
    academic_year_id = fields.Many2one('op.academic.year', 
        string='Учебный год', required=True, 
        default=lambda self: self._get_default_academic_year())
    student_ids = fields.Many2many('op.student', string='Ученики')

    @api.onchange('batch_id')
    def _onchange_batch_id(self):
        """Очищаем список выбранных учеников при смене класса, чтобы не было путаницы"""
        self.student_ids = [(5, 0, 0)]

    def action_print_report(self):
        data = {'form': self.read()[0]}
        return self.env.ref('openeducat_attendance.action_student_summary_report').report_action(self, data=data)

    # Функция для определения года по умолчанию
    def _get_default_academic_year(self):
        today = fields.Date.today()        
        year = self.env['op.academic.year'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today)
        ], limit=1)
        return year.id if year else False