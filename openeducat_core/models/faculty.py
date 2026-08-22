from odoo import _, api, fields, models


class OpFaculty(models.Model):
    _name = "op.faculty"
    _description = "OpenEduCat Faculty"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'op.person.base']
    _inherits = {"res.partner": "partner_id"}
    _parent_name = False

    partner_id = fields.Many2one('res.partner', 'Partner', required=True, ondelete="cascade")
    user_id = fields.Many2one('res.users', 'User', ondelete="cascade")
    
    login = fields.Char('Login', related='partner_id.user_id.login', readonly=True)
    last_login = fields.Datetime('Latest Connection', readonly=True, related='partner_id.user_id.login_date')
    faculty_subject_ids = fields.Many2many('op.subject', string='Subject(s)', tracking=True)
    homeroom_batch_ids = fields.Many2many(
        'op.batch', 'op_faculty_homeroom_batch_rel', 'faculty_id', 'batch_id',
        string='Классный руководитель', tracking=True,
        help='Классы (параллели/потоки), в которых этот учитель является классным руководителем.')
    current_homeroom_batch_ids = fields.Many2many(
        'op.batch', compute='_compute_current_homeroom_batch_ids',
        string='Классный руководитель (текущие)')

    @api.depends('homeroom_batch_ids')
    def _compute_current_homeroom_batch_ids(self):
        """Только классы текущего учебного периода (end_date не в прошлом)."""
        today = fields.Date.today()
        for faculty in self:
            faculty.current_homeroom_batch_ids = faculty.homeroom_batch_ids.filtered(
                lambda b: b.end_date and b.end_date >= today)
    emp_id = fields.Many2one('hr.employee', 'HR Employee')
    main_department_id = fields.Many2one(
        'op.department', 'Main Department',
        default=lambda self: self.env.user.dept_id and self.env.user.dept_id.id or False)
    allowed_department_ids = fields.Many2many(
        'op.department', string='Allowed Department',
        default=lambda self: self.env.user.department_ids and self.env.user.department_ids.ids or False)
    active = fields.Boolean(default=True)

    def create_employee(self):
        for record in self:
            vals = {
                'name': record.name,
                'country_id': record.nationality.id,
                'gender': record.gender,
            }
            emp_id = self.env['hr.employee'].create(vals)
            record.write({'emp_id': emp_id.id})
            record.partner_id.write({'partner_share': True, 'employee': True})

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Faculties'),
            'template': '/openeducat_core/static/xls/op_faculty.xls'
        }]

    class PartnerTitle(models.Model):
        _inherit = 'res.partner.title'

        @api.depends('shortcut')
        def _compute_display_name(self):
            for record in self:
                record.display_name = f"{record.shortcut}"
