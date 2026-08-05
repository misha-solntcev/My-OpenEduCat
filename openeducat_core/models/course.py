from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpCourse(models.Model):
    _name = "op.course"
    _inherit = "mail.thread"
    _description = "OpenEduCat Course"

    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('Code', size=16, required=True)
    parent_id = fields.Many2one('op.course', 'Parent Course')
    evaluation_type = fields.Selection(
        [('normal', 'Normal'), ('GPA', 'GPA'),
         ('CWA', 'CWA'), ('CCE', 'CCE')],
        'Evaluation Type', default="normal", required=True)
    subject_ids = fields.Many2many('op.subject', string='Subject(s)')
    max_unit_load = fields.Float("Maximum Unit Load")
    min_unit_load = fields.Float("Minimum Unit Load")
    department_id = fields.Many2one(
        'op.department', 'Department',
        default=lambda self:
        self.env.user.dept_id and self.env.user.dept_id.id or False)
    active = fields.Boolean(default=True)
    program_id = fields.Many2one('op.program', string="Program", tracking=True)

    _sql_constraints = [
        ('unique_course_code',
         'unique(code)', 'Code should be unique per course!')]

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive categories.'))

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Courses'),
            'template': '/openeducat_core/static/xls/op_course.xls'
        }]
