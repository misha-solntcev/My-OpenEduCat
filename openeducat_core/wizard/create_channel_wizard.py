from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CreateChannelWizard(models.TransientModel):
    _name = 'create.channel.wizard'
    _description = 'Create Chat Channels for Course'

    # Step 1: Course selection
    course_ids = fields.Many2many(
        'op.course', string='Courses',
        default=lambda self: self.env.context.get('active_ids'),
        relation='course_create_channel_rel',
    )

    # General channel
    general_channel_name = fields.Char(
        string='General Channel Name', default='Школа РОСТ', required=True
    )
    create_general_channel = fields.Boolean(
        string='Create/Update General School Channel', default=True
    )

    # Subject selection (populated on course change)
    subject_ids = fields.Many2many(
        'op.subject', string='Subjects to Create Channels For',
        help='Select which subjects should have dedicated channels',
    )
    subject_domain = fields.Char(
        string='Subject Domain', compute='_compute_subject_domain', readonly=True
    )

    # Student selection
    student_ids = fields.Many2many(
        'op.student', string='Students to Subscribe',
        help='Select students to subscribe to class and subject channels',
    )
    student_domain = fields.Char(
        string='Student Domain', compute='_compute_student_domain', readonly=True
    )

    # Teacher selection
    faculty_ids = fields.Many2many(
        'op.faculty', string='Teachers to Subscribe',
        help='Select teachers to subscribe to class and subject channels',
    )
    faculty_domain = fields.Char(
        string='Faculty Domain', compute='_compute_faculty_domain', readonly=True
    )

    # Options
    subscribe_students_to_subjects = fields.Boolean(
        string='Subscribe Students to Subject Channels', default=True
    )
    subscribe_teachers_to_subjects = fields.Boolean(
        string='Subscribe Teachers to Subject Channels', default=True
    )
    subscribe_all_to_general = fields.Boolean(
        string='Subscribe All to General Channel', default=True
    )

    @api.depends('course_ids')
    def _compute_subject_domain(self):
        for rec in self:
            if rec.course_ids:
                subject_ids = rec.course_ids.mapped('subject_ids').ids
                rec.subject_domain = str([('id', 'in', subject_ids)])
            else:
                rec.subject_domain = str([('id', '=', False)])

    @api.depends('course_ids')
    def _compute_student_domain(self):
        for rec in self:
            if rec.course_ids:
                # Get students enrolled in these courses via batches
                batches = self.env['op.batch'].search([
                    ('course_id', 'in', rec.course_ids.ids),
                    ('active', '=', True)
                ])
                student_ids = self.env['op.student'].search([
                    ('course_detail_ids.batch_id', 'in', batches.ids),
                    ('user_id', '!=', False),
                ]).ids
                rec.student_domain = str([('id', 'in', student_ids)])
            else:
                rec.student_domain = str([('id', '=', False)])

    @api.depends('course_ids')
    def _compute_faculty_domain(self):
        for rec in self:
            if rec.course_ids:
                batches = self.env['op.batch'].search([
                    ('course_id', 'in', rec.course_ids.ids),
                    ('active', '=', True)
                ])
                # Teachers who have sessions in these batches
                sessions = self.env['op.session'].search([
                    ('batch_id', 'in', batches.ids)
                ])
                faculty_ids = sessions.mapped('faculty_id').ids
                rec.faculty_domain = str([('id', 'in', faculty_ids)])
            else:
                rec.faculty_domain = str([('id', '=', False)])

    @api.onchange('course_ids')
    def _onchange_course_ids(self):
        """Auto-select all available subjects/students/teachers when courses change."""
        if self.course_ids:
            # Subjects from courses
            self.subject_ids = self.course_ids.mapped('subject_ids')
            
            # Students enrolled in these courses
            batches = self.env['op.batch'].search([
                ('course_id', 'in', self.course_ids.ids),
                ('active', '=', True)
            ])
            self.student_ids = self.env['op.student'].search([
                ('course_detail_ids.batch_id', 'in', batches.ids),
                ('user_id', '!=', False),
            ])
            
            # Teachers with sessions in these batches
            sessions = self.env['op.session'].search([
                ('batch_id', 'in', batches.ids)
            ])
            self.faculty_ids = sessions.mapped('faculty_id')
        else:
            self.subject_ids = False
            self.student_ids = False
            self.faculty_ids = False

    def _get_or_create_general_channel(self):
        """Create or get the school-wide General channel."""
        channel = self.env['discuss.channel'].search(
            [('name', '=', self.general_channel_name), ('channel_type', '=', 'channel')],
            limit=1
        )
        # General channel: all students group + admins
        student_group = self.env.ref('openeducat_core.group_op_students')
        admin_groups = self._get_admin_groups()
        all_groups = [(4, student_group.id)] + [(4, g.id) for g in admin_groups]
        
        if not channel:
            channel = self.env['discuss.channel'].create({
                'name': self.general_channel_name,
                'channel_type': 'channel',
                'description': 'Общие объявления для всей школы',
                'group_public_id': student_group.id,
                'group_ids': all_groups,
            })
        else:
            channel.write({'group_ids': all_groups})
        return channel

    def _get_class_group(self, batch):
        """Get class-specific group from batch name (e.g., '11 класс' -> 'Ученики 11 класс')."""
        import re
        match = re.match(r'^(\d+)\s', batch.name)
        if not match:
            return self.env.ref('openeducat_core.group_op_students')  # fallback
        class_num = int(match.group(1))
        if not (1 <= class_num <= 11):
            return self.env.ref('openeducat_core.group_op_students')
        
        group_name = f'Ученики {class_num} класс'
        group = self.env['res.groups'].search([('name', '=', group_name)], limit=1)
        if not group:
            # Create class group if not exists
            category = self.env.ref('openeducat_core.module_category_openeducat', raise_if_not_found=False)
            base_group_user = self.env.ref('base.group_user', raise_if_not_found=False)
            group = self.env['res.groups'].create({
                'name': group_name,
                'category_id': category.id if category else False,
                'implied_ids': [(4, base_group_user.id)] if base_group_user else [],
            })
        return group

    def _get_admin_groups(self):
        """Get ONLY admin groups that should have access to all channels."""
        groups = self.env['res.groups']
        # Back office admin group ONLY
        try:
            groups |= self.env.ref('openeducat_core.group_op_back_office_admin')
        except ValueError:
            pass
        return groups

    def _get_admin_partners(self):
        """Get partners of users in admin/teacher groups for auto-subscription."""
        admin_groups = self._get_admin_groups()
        users = self.env['res.users'].search([('groups_id', 'in', admin_groups.ids)])
        return users.mapped('partner_id')

    def _get_or_create_class_channel(self, batch):
        """Create or get class channel for a batch."""
        channel = self.env['discuss.channel'].search(
            [('name', '=ilike', batch.name), ('channel_type', '=', 'channel')],
            limit=1
        )
        # Use CLASS-SPECIFIC group (e.g., "Ученики 11 класс")
        class_group = self._get_class_group(batch)
        admin_groups = self._get_admin_groups()
        all_groups = [(4, class_group.id)] + [(4, g.id) for g in admin_groups]
        
        if not channel:
            channel = self.env['discuss.channel'].create({
                'name': batch.name,
                'channel_type': 'channel',
                'description': f'Классный канал для {batch.name}',
                'group_public_id': class_group.id,
                'group_ids': all_groups,
            })
        else:
            channel.write({'group_ids': all_groups})
        return channel

    def _get_or_create_subject_channel(self, batch, subject):
        """Create or get subject channel for a batch+subject."""
        channel_name = f"{batch.name} — {subject.name}"
        channel = self.env['discuss.channel'].search(
            [('name', '=ilike', channel_name), ('channel_type', '=', 'channel')],
            limit=1
        )
        # Use CLASS-SPECIFIC group (e.g., "Ученики 11 класс")
        class_group = self._get_class_group(batch)
        admin_groups = self._get_admin_groups()
        all_groups = [(4, class_group.id)] + [(4, g.id) for g in admin_groups]
        
        if not channel:
            channel = self.env['discuss.channel'].create({
                'name': channel_name,
                'channel_type': 'channel',
                'description': f'{subject.display_name} — {batch.name}',
                'group_public_id': class_group.id,
                'group_ids': all_groups,
            })
        else:
            channel.write({'group_ids': all_groups})
        return channel

    def _subscribe_partners(self, channel, partners):
        """Subscribe partners to channel (idempotent)."""
        existing = channel.channel_partner_ids
        for partner in partners:
            if partner not in existing:
                self.env['discuss.channel.member'].create({
                    'channel_id': channel.id,
                    'partner_id': partner.id,
                    'fold_state': 'open',
                })

    def action_create_channels(self):
        """Create channels based on wizard selections."""
        self.ensure_one()
        
        created_channels = []
        updated_channels = []
        
        # General channel
        general_channel = None
        if self.create_general_channel:
            general_channel = self._get_or_create_general_channel()
            if general_channel.id not in [c.id for c in created_channels + updated_channels]:
                created_channels.append(general_channel)
        
        # Process each course
        for course in self.course_ids:
            # Get active batch for this course
            batch = self.env['op.batch'].search([
                ('course_id', '=', course.id),
                ('active', '=', True)
            ], limit=1)
            
            if not batch:
                raise UserError(
                    _('Active batch not found for course "%s".') % course.name
                )
            
            # Get selected students/teachers for THIS course
            course_batches = self.env['op.batch'].search([
                ('course_id', '=', course.id),
                ('active', '=', True)
            ])
            
            course_students = self.student_ids.filtered(
                lambda s: s.course_detail_ids.batch_id in course_batches
            )
            course_faculty = self.faculty_ids.filtered(
                lambda f: self.env['op.session'].search_count([
                    ('batch_id', 'in', course_batches.ids),
                    ('faculty_id', '=', f.id)
                ]) > 0
            )
            
            student_partners = course_students.mapped('user_id.partner_id')
            faculty_partners = course_faculty.mapped('user_id.partner_id')
            
            # --- Class Channel ---
            class_channel = self._get_or_create_class_channel(batch)
            if class_channel.id not in [c.id for c in created_channels + updated_channels]:
                created_channels.append(class_channel)
            
            # Subscribe selected students + teachers to class channel
            class_partners = student_partners | faculty_partners
            # Also auto-subscribe admins/teachers with access rights
            admin_partners = self._get_admin_partners()
            class_partners |= admin_partners
            self._subscribe_partners(class_channel, class_partners)
            
            # Also add to general channel
            if general_channel and self.subscribe_all_to_general:
                general_partners = class_partners
                self._subscribe_partners(general_channel, general_partners)
            
            # --- Subject Channels ---
            for subject in self.subject_ids.filtered(lambda s: s in course.subject_ids):
                subject_channel = self._get_or_create_subject_channel(batch, subject)
                if subject_channel.id not in [c.id for c in created_channels + updated_channels]:
                    created_channels.append(subject_channel)
                
                # Subscribe students to subject channel
                if self.subscribe_students_to_subjects:
                    subject_partners = student_partners
                    # Also add admins
                    admin_partners = self._get_admin_partners()
                    subject_partners |= admin_partners
                    self._subscribe_partners(subject_channel, subject_partners)
                
                # Subscribe teachers of THIS subject
                if self.subscribe_teachers_to_subjects:
                    subject_sessions = self.env['op.session'].search([
                        ('batch_id', 'in', course_batches.ids),
                        ('subject_id', '=', subject.id)
                    ])
                    subject_faculty = subject_sessions.mapped('faculty_id')
                    selected_subject_faculty = subject_faculty & self.faculty_ids
                    subject_faculty_partners = selected_subject_faculty.mapped('user_id.partner_id')
                    # Also add admins
                    admin_partners = self._get_admin_partners()
                    subject_faculty_partners |= admin_partners
                    self._subscribe_partners(subject_channel, subject_faculty_partners)
        
        # Prepare result message
        total_subject_channels = len(created_channels) - len(self.course_ids) - (1 if general_channel else 0)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Channels Created/Updated'),
                'message': _(
                    'Done! Created: %d class channel(s), %d subject channel(s)%s. '
                    'Participants subscribed per your selection.'
                ) % (
                    len(self.course_ids),
                    max(0, total_subject_channels),
                    ', 1 general channel' if general_channel else '',
                ),
                'type': 'success',
                'sticky': False,
            },
        }