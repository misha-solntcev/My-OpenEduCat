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
    academic_years_id = fields.Many2one('op.academic.year', 'Academic Year', required=True, tracking=True)
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

    # === Single Source of Truth ===
    current_course_detail_id = fields.Many2one(
        'op.student.course',
        string="Текущее зачисление",
        compute='_compute_current_course_detail',
        store=True,
    )
    # Быстрые readonly-поля через текущую запись
    active_course_id = fields.Many2one(
        related='current_course_detail_id.course_id',
        string='Текущий курс',
        store=True,
        readonly=True,
    )
    active_batch_id = fields.Many2one(
        related='current_course_detail_id.batch_id',
        string='Текущий класс',
        store=True,
        readonly=True,
    )
    active_academic_year_id = fields.Many2one(
        related='current_course_detail_id.academic_years_id',
        string='Текущий учебный год',
        store=True,
        readonly=True,
    )

    # Student state for form view statusbar
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('admission', 'Зачислен'),
        ('studying', 'Обучается'),
        ('left', 'Ушел/Отчислен'),
        ('pass_out', 'Выпускник'),
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

    _sql_constraints = [(
        'unique_gr_no',
        'unique(gr_no)',
        'Registration Number must be unique per student!'
    )]

    @api.depends('course_detail_ids.state', 'course_detail_ids.academic_years_id')
    def _compute_current_course_detail(self):
        for student in self:
            running = student.course_detail_ids.filtered(lambda r: r.state == 'running')
            # Если есть несколько running, берём с максимальным start_date года
            if running:
                student.current_course_detail_id = max(
                    running,
                    key=lambda r: r.academic_years_id.start_date if r.academic_years_id else '0001-01-01'
                )
            else:
                student.current_course_detail_id = False

    # Historical computed fields (stored — required by searchpanel/read_group)
    last_active_course_id = fields.Many2one(
        'op.course', string='Last Completed Course',
        compute='_compute_last_completed_course', store=True
    )
    last_active_academic_year_id = fields.Many2one(
        'op.academic.year', string='Last Academic Year',
        compute='_compute_last_completed_course', store=True
    )

    @api.depends('course_detail_ids.state', 'course_detail_ids.academic_years_id', 'course_detail_ids.course_id')
    def _compute_last_completed_course(self):
        for student in self:
            finished = student.course_detail_ids.filtered(lambda r: r.state == 'finished')
            if finished:
                last = max(finished, key=lambda r: (
                    r.academic_years_id.start_date if r.academic_years_id else '0001-01-01'))
                student.last_active_course_id = last.course_id
                student.last_active_academic_year_id = last.academic_years_id
            else:
                student.last_active_course_id = False
                student.last_active_academic_year_id = False

    @api.constrains('state', 'course_detail_ids')
    def _check_student_state_consistency(self):
        """Единый constraint вместо трёх разрозненных.
        Допускает одновременное наличие finished и running записей
        (переходный период между учебными годами)."""
        for student in self:
            has_running = any(c.state == 'running' for c in student.course_detail_ids)
            has_finished = any(c.state == 'finished' for c in student.course_detail_ids)

            if student.state == 'studying' and not has_running:
                raise ValidationError(
                    _("Ученик в статусе 'Обучается' должен иметь хотя бы один активный курс (state='running').")
                )
            if student.state in ('pass_out', 'left') and not has_finished:
                raise ValidationError(
                    _("Ученик в статусе '%s' должен иметь хотя бы одну завершённую запись курса.")
                    % dict(self._fields['state'].selection)[student.state]
                )

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Students'),
            'template': '/openeducat_core/static/xls/op_student.xls'
        }]

    def create_student_user(self):
        """Создает системного пользователя для ученика."""
        user_group = self.env.ref("openeducat_core.group_op_students", raise_if_not_found=False)
        for record in self.filtered(lambda s: not s.user_id and s.email):
            group_commands = [fields.Command.link(user_group.id)] if user_group else []
            record.user_id = self.env["res.users"].create({
                "name": record.name,
                "partner_id": record.partner_id.id,
                "login": record.email,
                "email": record.email,
                "groups_id": group_commands,
                "tz": self.env.context.get("tz", "UTC"),
            })