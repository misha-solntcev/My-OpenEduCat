from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StudentMigrate(models.TransientModel):
    """ Student Migration Wizard """
    _name = "student.migrate"
    _description = "Student Migrate"

    date = fields.Date('Date', required=True, default=fields.Date.today)
    course_from_id = fields.Many2one('op.course', 'From Course', required=True)
    course_to_id = fields.Many2one('op.course', 'To Course')
    batch_id = fields.Many2one('op.batch', 'To Batch')
    optional_sub = fields.Boolean("Optional Subjects")
    student_ids = fields.Many2many(
        'op.student', string='Student(s)', required=True)
    course_completed = fields.Boolean(string="Course Completed?")

    @api.onchange('course_from_id')
    def student_by_course(self):
        self.student_ids = False
        if not self.course_from_id:
            return {'domain': {'student_ids': []}}

        running_courses = self.env['op.student.course'].search([
            ('course_id', '=', self.course_from_id.id),
            ('state', '=', 'running')
        ])
        return {
            'domain': {
                'student_ids': [('id', 'in', running_courses.mapped('student_id').ids)]
            }
        }

    @api.constrains('course_from_id', 'course_to_id', 'course_completed')
    def _check_migration_courses(self):
        for record in self:
            if not record.course_completed and not record.course_to_id:
                raise ValidationError(
                    _("Please select 'To Course' or mark as 'Course Completed'."))

            if record.course_to_id and record.course_from_id == record.course_to_id:
                raise ValidationError(
                    _("From Course must not be same as To Course!"))

            if record.course_from_id.parent_id:
                if record.course_to_id:
                    if record.course_from_id.parent_id != record.course_to_id.parent_id:
                        raise ValidationError(_(
                            "Can't migrate, As selected courses don't share same parent course!"))  # noqa
                elif not record.course_completed:
                    raise ValidationError(
                        _("Can't migrate, Proceed for new admission"))

    def _get_academic_year_from_batch(self, batch):
        """Find academic year that encompasses the batch dates."""
        if not batch or not batch.start_date or not batch.end_date:
            return False
        return self.env['op.academic.year'].search([
            ('start_date', '<=', batch.start_date),
            ('end_date', '>=', batch.end_date)
        ], limit=1)

    def student_migrate_forward(self):
        act_type = self.env.ref(
            'openeducat_activity.op_activity_type_3', raise_if_not_found=False)
        act_type_id = act_type.id if act_type else False

        for record in self:
            academic_year = (
                record._get_academic_year_from_batch(record.batch_id)
                if not record.course_completed
                else False
            )

            activities_to_create = []
            student_courses_to_create = []
            registrations_to_create = []

            # Finish all running courses for these students at once
            target_student_courses = record.student_ids.mapped(
                'course_detail_ids'
            ).filtered(
                lambda sc: sc.course_id == record.course_from_id
                and sc.state == 'running'
            )
            target_student_courses.write({'state': 'finished'})

            # Sync student state based on course_completed flag
            if record.course_completed:
                record.student_ids.write({'state': 'pass_out'})

            for student in record.student_ids:
                if record.course_completed:
                    desc = _(
                        "Migration From %s to Completed Course"
                    ) % record.course_from_id.name
                else:
                    desc = _(
                        "Migration from %s to %s"
                    ) % (record.course_from_id.name, record.course_to_id.name)
                    # Ensure student is in studying state when migrating to new course
                    if student.state not in ['studying', 'admission']:
                        student.write({'state': 'studying'})

                    student_courses_to_create.append({
                        'student_id': student.id,
                        'course_id': record.course_to_id.id,
                        'batch_id': record.batch_id.id if record.batch_id else False,
                        'subject_ids': [(6, 0, record.course_to_id.subject_ids.ids)],
                        'academic_years_id': academic_year.id if academic_year else False,
                    })

                if act_type_id:
                    activities_to_create.append({
                        'student_id': student.id,
                        'type_id': act_type_id,
                        'date': record.date,
                        'description': desc,
                    })

                if not record.course_completed and record.course_to_id:
                    registrations_to_create.append({
                        'student_id': student.id,
                        'batch_id': record.batch_id.id if record.batch_id else False,
                        'course_id': record.course_to_id.id,
                        'min_unit_load': record.course_to_id.min_unit_load or 0.0,
                        'max_unit_load': record.course_to_id.max_unit_load or 0.0,
                        'state': 'draft',
                    })

            # Bulk operations
            if activities_to_create:
                self.env['op.activity'].create(activities_to_create)

            if student_courses_to_create:
                self.env['op.student.course'].create(student_courses_to_create)

            if registrations_to_create:
                registrations = self.env['op.subject.registration'].create(
                    registrations_to_create
                )
                registrations.get_subjects()
                if not record.optional_sub:
                    registrations.action_submitted()
                    registrations.action_approve()
