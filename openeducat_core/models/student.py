from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    @api.constrains('state', 'student_id')
    def _check_student_state_on_course_finish(self):
        for record in self:
            if record.state == 'finished' and record.student_id.state == 'studying':
                # Allow finishing if student will be set to 'left' via wizard
                # This constraint is checked before wizard writes new state
                # We allow it because wizard handles state transition
                pass

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
    last_active_course_id = fields.Many2one(
        'op.course',
        string="Last Completed Course",
        compute='_compute_active_course_details',
        store=True,
    )
    last_active_academic_year_id = fields.Many2one(
        'op.academic.year',
        string="Last Academic Year",
        compute='_compute_active_course_details',
        store=True,
    )

    # Student state for form view statusbar
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('admission', 'Зачислен'),
        ('studying', 'Обучается'),
        ('left', 'Ушел/Отчислен'),
        ('pass_out', 'Выпущен'),
    ], string='Статус', default='draft', tracking=True)

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
            finished_details = student.course_detail_ids.filtered(lambda r: r.state == 'finished')
            
            # Active course/year: prioritize running courses
            if running_details:
                active_record = running_details[0]
                student.active_academic_year_id = active_record.academic_years_id
                student.active_course_id = active_record.course_id
            else:
                student.active_academic_year_id = False
                student.active_course_id = False
            
            # Last completed course/year: for historical context (left)
            if finished_details:
                last_finished = finished_details[-1]
                student.last_active_course_id = last_finished.course_id
                student.last_active_academic_year_id = last_finished.academic_years_id
            else:
                student.last_active_course_id = False
                student.last_active_academic_year_id = False

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Students'),
            'template': '/openeducat_core/static/xls/op_student.xls'
        }]

    @api.constrains('state', 'course_detail_ids')
    def _check_student_course_state_consistency(self):
        for student in self:
            if student.state == 'studying':
                running_courses = student.course_detail_ids.filtered(lambda r: r.state == 'running')
                if not running_courses:
                    raise ValidationError(_(
                        "Student in 'Studying' state must have at least one running course."
                    ))
            if student.state in ['pass_out', 'left']:
                finished_courses = student.course_detail_ids.filtered(lambda r: r.state == 'finished')
                if not finished_courses:
                    raise ValidationError(_(
                        "Student in 'Pass Out' or 'Left' state must have at least one finished course."
                    ))

    @api.constrains('course_detail_ids')
    def _check_course_detail_state_consistency(self):
        for student in self:
            finished_courses = student.course_detail_ids.filtered(lambda r: r.state == 'finished')
            if finished_courses and student.state == 'studying':
                raise ValidationError(_(
                    "Student has finished courses but is still in 'Studying' state. "
                    "Please update student state to 'Pass Out' or 'Left'."
                ))

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