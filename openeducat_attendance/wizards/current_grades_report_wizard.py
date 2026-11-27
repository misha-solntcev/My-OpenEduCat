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

    # Предметы, которые реально ведутся в выбранных классах за выбранный год.
    # Предметы в школе общие на всю школу, а уроки — по классам: английский в
    # 6 А 2026/27 разбит на «Английский язык А»/«Английский язык Б», и общего
    # «Английского языка» в этом классе в этом году нет. Выбор такого предмета
    # давал пустой отчёт (шапка без единой строки), хотя отчёт исправен.
    # Доменом ограничиваем выбор теми предметами, по которым в классах есть
    # уроки — отчёт читает именно строки журнала, поэтому список совпадает с
    # тем, что может напечататься.
    available_subject_ids = fields.Many2many(
        'op.subject', 'current_grades_wizard_available_subject_rel',
        'wizard_id', 'subject_id', string='Доступные предметы',
        compute='_compute_available_subject_ids',
        help='Предметы, по которым в выбранных классах есть уроки за выбранный учебный год')

    def _get_default_year(self):
        return self.env['op.academic.year'].search([
            ('start_date', '<=', fields.Date.today()),
            ('end_date', '>=', fields.Date.today())
        ], limit=1).id

    @api.depends('academic_year_id', 'batch_ids')
    def _compute_available_subject_ids(self):
        for wizard in self:
            wizard.available_subject_ids = wizard._get_available_subjects()

    def _get_available_subjects(self):
        """Предметы, по которым в выбранных классах есть уроки за год.

        Сузить список можно только при выбранных классах — без них вернём все.
        Если журналов за год ещё нет (начало сентября), берём набор предметов
        из зачислений этих классов, чтобы список не был пустым.
        """
        self.ensure_one()
        all_subjects = self.env['op.subject'].search([])
        year = self.academic_year_id
        if not self.batch_ids or not year.start_date:
            return all_subjects

        groups = self.env['op.attendance.line']._read_group([
            ('batch_id', 'in', self.batch_ids.ids),
            ('attendance_date', '>=', year.start_date),
            ('attendance_date', '<=', year.end_date),
        ], ['subject_id'], [])
        subjects = all_subjects.browse([group[0].id for group in groups if group[0]])
        if subjects:
            return subjects

        courses = self.env['op.student.course'].search([
            ('batch_id', 'in', self.batch_ids.ids),
            ('academic_years_id', '=', year.id),
        ])
        return courses.mapped('subject_ids') or all_subjects

    @api.onchange('batch_ids')
    def _onchange_batch_ids(self):
        self.student_ids = [(5, 0, 0)]

    @api.onchange('academic_year_id', 'batch_ids')
    def _onchange_available_subjects(self):
        # Уже выбранный предмет, которого нет в новых классах, снимаем —
        # иначе фильтр молча останется и отчёт снова выйдет пустым.
        # Сравниваем по id: в onchange-контексте записи виртуальные (NewId),
        # и проверка `subject in available` на них всегда ложна.
        available_ids = set(self._get_available_subjects().ids)
        keep_ids = [sid for sid in self.subject_ids.ids if sid in available_ids]
        self.subject_ids = [(6, 0, keep_ids)]

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('openeducat_attendance.action_report_current_grades').report_action(self)