from odoo import _, api, fields, models


class OpStudentCourse(models.Model):
    _name = "op.student.course"
    _description = "Student Course Details"
    _inherit = "mail.thread"
    _rec_name = 'student_id'

    student_id = fields.Many2one('op.student', 'Student',
                                 ondelete="cascade", tracking=True)
    course_id = fields.Many2one('op.course', 'Course', required=True, tracking=True)
    batch_id = fields.Many2one('op.batch', 'Batch', tracking=True)
    roll_number = fields.Char('Roll Number', tracking=True)
    subject_ids = fields.Many2many('op.subject', string='Subjects')
    academic_years_id = fields.Many2one('op.academic.year', 'Academic Year')
    academic_term_id = fields.Many2one('op.academic.term', 'Terms')
    state = fields.Selection([('running', 'Running'),
                              ('finished', 'Finished')],
                             string="Status", default="running")

    _sql_constraints = [
        ('unique_name_roll_number_id',
         'unique(roll_number,course_id,batch_id,student_id)',
         'Roll Number & Student must be unique per Batch!'),
        ('unique_name_roll_number_course_id',
         'unique(roll_number,course_id,batch_id)',
         'Roll Number must be unique per Batch!'),
        ('unique_name_roll_number_student_id',
         'unique(student_id,course_id,batch_id)',
         'Student must be unique per Batch!'),
    ]

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Student Course Details'),
            'template': '/openeducat_core/static/xls/op_student_course.xls'
        }]


class OpStudent(models.Model):
    _name = "op.student"
    _description = "Student"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'op.person.base']
    _inherits = {"res.partner": "partner_id"}
    _order = "name"
    _parent_name = False

    partner_id = fields.Many2one('res.partner', 'Partner', required=True, ondelete="cascade")
    user_id = fields.Many2one('res.users', 'User', ondelete="cascade")
    gr_no = fields.Char("Registration Number", size=20)
    category_id = fields.Many2one('op.category', 'Category')
    course_detail_ids = fields.One2many('op.student.course', 'student_id', 'Course Details', tracking=True)
    active = fields.Boolean(default=True)

    # Computed stored fields for accurate current class/academic year filtering
    active_academic_year_id = fields.Many2one(
        'op.academic.year',
        string="Current Academic Year",
        compute='_compute_active_course_details',
        store=True,
    )
    active_course_id = fields.Many2one(
        'op.course',
        string="Current Course",
        compute='_compute_active_course_details',
        store=True,
    )

    # Student state for form view statusbar
    state = fields.Selection([
        ('draft', 'Draft'),
        ('admission', 'Admission'),
        ('studying', 'Studying'),
        ('pass_out', 'Pass Out'),
        ('alumni', 'Alumni')
    ], string='Status', default='draft', tracking=True)

    # Fields from database (matching actual DB columns)
    birth_date = fields.Date('Birth Date')
    mobile = fields.Char('Mobile')
    email = fields.Char('Email')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    state_id = fields.Many2one('res.country.state', 'State')
    zip = fields.Char('ZIP')
    country_id = fields.Many2one('res.country', 'Country')
    emergency_contact = fields.Many2one('res.partner', 'Emergency Contact')
    emergency_phone = fields.Char('Emergency Phone')
    father_name = fields.Char("Father's Name")
    father_occupation = fields.Char("Father's Occupation")
    mother_name = fields.Char("Mother's Name")
    mother_occupation = fields.Char("Mother's Occupation")
    last_school = fields.Char('Last School')
    last_class = fields.Char('Last Class')
    library_card_id = fields.Many2one('op.library.card', 'Library Card')

    _sql_constraints = [(
        'unique_gr_no',
        'unique(gr_no)',
        'Registration Number must be unique per student!'
    )]

    @api.depends('course_detail_ids', 'course_detail_ids.state', 'course_detail_ids.academic_years_id', 'course_detail_ids.course_id')
    def _compute_active_course_details(self):
        for student in self:
            running_details = student.course_detail_ids.filtered(lambda r: r.state == 'running')
            if running_details:
                active_record = running_details[0]
                student.active_academic_year_id = active_record.academic_years_id
                student.active_course_id = active_record.course_id
            else:
                student.active_academic_year_id = False
                student.active_course_id = False

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Students'),
            'template': '/openeducat_core/static/xls/op_student.xls'
        }]

    def create_student_user(self):
        user_group = self.env.ref("base.group_portal") or False
        users_res = self.env['res.users']
        for record in self:
            if not record.user_id:
                user_id = users_res.create({
                    'name': record.name,
                    'partner_id': record.partner_id.id,
                    'login': record.email,
                    'groups_id': user_group,
                    'is_student': True,
                    'tz': self._context.get('tz'),
                })
                record.user_id = user_id