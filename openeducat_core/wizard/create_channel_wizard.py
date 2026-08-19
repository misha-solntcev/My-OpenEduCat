import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CreateChannelWizard(models.TransientModel):
    _name = 'create.channel.wizard'
    _description = 'Create Chat Channels for Courses'

    academic_year_id = fields.Many2one(
        'op.academic.year',
        string='Учебный год',
        default=lambda self: self._default_academic_year_id(),
        required=True,
    )
    course_ids = fields.Many2many('op.course', string='Курсы/Классы')
    create_general_channel = fields.Boolean('Создать общий канал', default=True)
    general_channel_name = fields.Char('Имя общего канала', default='Школа РОСТ')
    subscribe_students = fields.Boolean('Подписывать учеников на предметные каналы', default=True)
    subscribe_teachers = fields.Boolean('Подписывать учителей на предметные каналы', default=True)
    course_line_ids = fields.One2many(
        'create.channel.wizard.course', 'wizard_id', string='Классы/Потоки'
    )

    # ---------- defaults ----------

    @api.model
    def _default_academic_year_id(self):
        """Автовыбор текущего учебного года."""
        today = fields.Date.today()
        year = self.env['op.academic.year'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today),
        ], limit=1)
        if not year:
            year = self.env['op.academic.year'].search(
                [], order='start_date desc', limit=1)
        return year.id if year else None

    # ---------- line generation ----------

    def _rebuild_course_lines(self):
        """Пересобирает строки мастера на базе активных записей op.student.course."""
        if not self.course_ids or not self.academic_year_id:
            self.course_line_ids = [fields.Command.clear()]
            return

        enrollments = self.env['op.student.course'].search([
            ('academic_years_id', '=', self.academic_year_id.id),
            ('course_id', 'in', self.course_ids.ids),
            ('state', '=', 'running'),
        ])

        batches = enrollments.mapped('batch_id')
        commands = [fields.Command.clear()]

        for batch in batches:
            batch_enrollments = enrollments.filtered(lambda e: e.batch_id == batch)
            students = batch_enrollments.mapped('student_id').filtered(lambda s: s.user_id)
            faculty = self.env['op.session'].search([
                ('batch_id', '=', batch.id)
            ]).mapped('faculty_id').filtered(lambda f: f.user_id)

            commands.append(fields.Command.create({
                'academic_year_id': self.academic_year_id.id,
                'course_id': batch.course_id.id,
                'batch_id': batch.id,
                'subject_ids': [fields.Command.set(batch.course_id.subject_ids.ids)],
                'student_ids': [fields.Command.set(students.ids)],
                'faculty_ids': [fields.Command.set(faculty.ids)],
            }))

        self.course_line_ids = commands

    @api.onchange('academic_year_id', 'course_ids')
    def _onchange_academic_year_and_courses(self):
        """Пересобирает строки при изменении года или списка курсов."""
        self._rebuild_course_lines()

    # ---------- admin helpers ----------

    @api.model
    def _get_admin_partners(self):
        admin_group = self.env.ref('openeducat_core.group_op_back_office_admin', raise_if_not_found=False)
        if not admin_group:
            return self.env['res.partner']
        return self.env['res.users'].search([('groups_id', 'in', admin_group.id)]).mapped('partner_id')

    # ---------- class group ----------

    def _get_class_group(self, batch):
        """Поиск группы учеников соответствующего класса по регулярному выражению."""
        match = re.match(r'^(\d+)', batch.name or '')
        if match:
            class_num = int(match.group(1))
            if 1 <= class_num <= 11:
                group = self.env['res.groups'].search([('name', '=', f'Ученики {class_num} класс')], limit=1)
                if group:
                    return group
        return self.env.ref('openeducat_core.group_op_students', raise_if_not_found=False)

    # ---------- channel helpers ----------

    def _get_or_create_channel(self, name, description, group=None):
        channel = self.env['discuss.channel'].search([
            ('name', '=', name),
            ('channel_type', '=', 'channel')
        ], limit=1)

        values = {
            'name': name,
            'description': description,
            'channel_type': 'channel',
        }
        if group:
            values['group_public_id'] = group.id
            values['group_ids'] = [fields.Command.link(group.id)]

        if not channel:
            channel = self.env['discuss.channel'].create(values)
        elif group:
            channel.write({'group_ids': [fields.Command.link(group.id)], 'description': description})
        return channel

    def _channel_name(self, batch):
        year_name = self.academic_year_id.name or ''
        if year_name and year_name not in (batch.name or ''):
            return f'{batch.name} ({year_name})'
        return batch.name

    # ---------- main action ----------

    def action_create_channels(self):
        self.ensure_one()

        if self.course_ids and not self.course_line_ids:
            self._rebuild_course_lines()

        if not self.course_line_ids and not self.create_general_channel:
            raise UserError(_('Выберите учебный год и хотя бы один класс, либо создайте общий канал.'))

        admin_partners = self._get_admin_partners()
        created_counts = {'class': 0, 'subject': 0, 'general': 0}

        # Prefetch all sessions for all batches in one query
        batch_ids = self.course_line_ids.mapped('batch_id').ids
        all_sessions = self.env['op.session'].search([
            ('batch_id', 'in', batch_ids)
        ])
        # Group sessions by batch_id and subject_id for fast lookup
        sessions_by_batch = {}
        for session in all_sessions:
            key = (session.batch_id.id, session.subject_id.id)
            if key not in sessions_by_batch:
                sessions_by_batch[key] = self.env['op.session']
            sessions_by_batch[key] |= session

        # 1. Общий канал
        general_channel = None
        if self.create_general_channel:
            if not self.general_channel_name:
                raise UserError(_('Укажите имя общего канала.'))
            student_group = self.env.ref('openeducat_core.group_op_students', raise_if_not_found=False)
            general_channel = self._get_or_create_channel(
                self.general_channel_name, 'Общие объявления школы', student_group
            )
            created_counts['general'] = 1

        # 2. Каналы классов и предметов
        all_class_partners = self.env['res.partner']
        class_channels = {}  # batch_id -> channel
        subject_channels = {}  # (batch_id, subject_id) -> channel

        # First pass: create/get all channels
        for line in self.course_line_ids:
            batch = line.batch_id
            class_group = self._get_class_group(batch)
            ch_name = self._channel_name(batch)

            class_channel = self._get_or_create_channel(
                ch_name, f'Классный канал: {ch_name}', class_group
            )
            class_channels[batch.id] = class_channel
            created_counts['class'] += 1

            for subject in line.subject_ids:
                sub_name = f'{ch_name} — {subject.display_name}'
                subj_channel = self._get_or_create_channel(
                    sub_name, f'Предмет: {subject.display_name} ({ch_name})', class_group
                )
                subject_channels[(batch.id, subject.id)] = subj_channel
                created_counts['subject'] += 1

        # Second pass: collect all partners per channel and bulk subscribe
        # Class channels
        for line in self.course_line_ids:
            batch = line.batch_id
            class_channel = class_channels[batch.id]

            student_partners = line.student_ids.mapped('user_id.partner_id')
            faculty_partners = line.faculty_ids.mapped('user_id.partner_id')
            all_partners = student_partners | faculty_partners | admin_partners
            all_class_partners |= all_partners

            class_channel.add_members(partner_ids=all_partners.ids)

        # General channel - add all class partners at once
        if general_channel:
            general_channel.add_members(partner_ids=all_class_partners.ids)

        # Subject channels
        for line in self.course_line_ids:
            batch = line.batch_id
            student_partners = line.student_ids.mapped('user_id.partner_id')
            faculty_partners = line.faculty_ids.mapped('user_id.partner_id')

            for subject in line.subject_ids:
                subj_channel = subject_channels[(batch.id, subject.id)]

                sub_partners = admin_partners
                if self.subscribe_students:
                    sub_partners |= student_partners
                if self.subscribe_teachers:
                    sessions = sessions_by_batch.get((batch.id, subject.id), self.env['op.session'])
                    sub_faculty = sessions.mapped('faculty_id') & line.faculty_ids
                    sub_partners |= sub_faculty.mapped('user_id.partner_id')

                subj_channel.add_members(partner_ids=sub_partners.ids)

        parts = [f'{count} {label}' for label, count in [
            ('общий', created_counts['general']),
            ('классных', created_counts['class']),
            ('предметных', created_counts['subject'])
        ] if count > 0]

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Каналы синхронизированы'),
                'message': _('Обработано: %s.') % ', '.join(parts),
                'type': 'success',
                'sticky': False,
            },
        }


class CreateChannelWizardCourse(models.TransientModel):
    _name = 'create.channel.wizard.course'
    _description = 'Course line for channel creation'

    wizard_id = fields.Many2one('create.channel.wizard', required=True, ondelete='cascade')
    academic_year_id = fields.Many2one('op.academic.year', string='Учебный год', required=True)
    course_id = fields.Many2one('op.course', string='Курс', required=True)
    batch_id = fields.Many2one('op.batch', string='Класс/Поток', required=True)
    subject_ids = fields.Many2many('op.subject', string='Предметы', readonly=False)
    student_ids = fields.Many2many('op.student', string='Ученики', readonly=False)
    faculty_ids = fields.Many2many('op.faculty', string='Учителя', readonly=False)

    # Preview counts (computed, not stored)
    student_count = fields.Integer(string='Учеников', compute='_compute_counts')
    faculty_count = fields.Integer(string='Учителей', compute='_compute_counts')
    subject_count = fields.Integer(string='Предметов', compute='_compute_counts')

    @api.depends('batch_id', 'wizard_id.academic_year_id')
    def _compute_counts(self):
        for line in self:
            wizard = line.wizard_id
            if not wizard.academic_year_id or not line.batch_id:
                line.update(dict(student_count=0, faculty_count=0, subject_count=0))
                continue
            sc = self.env['op.student.course'].search([
                ('academic_years_id', '=', wizard.academic_year_id.id),
                ('batch_id', '=', line.batch_id.id),
                ('state', '=', 'running'),
                ('student_id.user_id', '!=', False),
            ])
            sessions = self.env['op.session'].search([
                ('batch_id', '=', line.batch_id.id),
            ])
            line.student_count = len(sc.mapped('student_id'))
            line.faculty_count = len(sessions.mapped('faculty_id'))
            line.subject_count = len(line.batch_id.course_id.subject_ids)