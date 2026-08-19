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
        return year.id if year else False

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
        if not batches:
            self.course_line_ids = [fields.Command.clear()]
            return

        # Prefetch: группируем записи зачислений по batch_id (O(n) вместо O(n×m))
        enrollments_by_batch = {}
        for e in enrollments:
            enrollments_by_batch.setdefault(e.batch_id.id, self.env['op.student.course'])
            enrollments_by_batch[e.batch_id.id] |= e

        # Prefetch: загружаем все сессии для всех классов одним запросом
        all_sessions = self.env['op.session'].search([('batch_id', 'in', batches.ids)])
        sessions_by_batch = {}
        for session in all_sessions:
            sessions_by_batch.setdefault(session.batch_id.id, self.env['op.session'])
            sessions_by_batch[session.batch_id.id] |= session

        commands = [fields.Command.clear()]

        for batch in batches:
            batch_enrollments = enrollments_by_batch.get(batch.id, self.env['op.student.course'])
            students = batch_enrollments.mapped('student_id').filtered(lambda s: s.user_id)
            
            # Берем сессии из кэша, а не из БД
            batch_sessions = sessions_by_batch.get(batch.id, self.env['op.session'])
            faculty = batch_sessions.mapped('faculty_id').filtered(lambda f: f.user_id)

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
        return self.env['res.users'].search([('groups_id', 'in', admin_group.ids)]).mapped('partner_id')

    # ---------- channel helpers ----------

    def _channel_name(self, batch):
        year_name = self.academic_year_id.name or ''
        if year_name and year_name not in (batch.name or ''):
            return f'{batch.name} ({year_name})'
        return batch.name

    # ---------- main action ----------

    def action_create_channels(self):
        self.ensure_one()

        # CRITICAL: Отключаем трекинг и mail для массовых операций (ускорение в 5-10 раз)
        self = self.with_context(
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
            mail_auto_subscribe=False,
        )
        env = self.env

        if self.course_ids and not self.course_line_ids:
            self._rebuild_course_lines()

        if not self.course_line_ids and not self.create_general_channel:
            raise UserError(_('Выберите учебный год и хотя бы один класс, либо создайте общий канал.'))

        # 1. Предзагрузка админов (через helper, без дублирования)
        admin_partners = self._get_admin_partners()
        admin_partner_ids = set(admin_partners.ids)
        admin_group = self.env.ref('openeducat_core.group_op_back_office_admin', raise_if_not_found=False)
        admin_group_ids = [admin_group.id] if admin_group else []

        # 2. Кэшируем class_groups (один search вместо N)
        class_groups_records = env['res.groups'].search([('name', '=like', 'Ученики % класс')])
        class_group_cache = {g.name: g for g in class_groups_records}
        default_student_group = env.ref('openeducat_core.group_op_students', raise_if_not_found=False)

        def get_cached_class_group(batch_name):
            match = re.match(r'^(\d+)', batch_name or '')
            if match:
                num = int(match.group(1))
                if 1 <= num <= 11:
                    name_key = f'Ученики {num} класс'
                    if name_key in class_group_cache:
                        return class_group_cache[name_key]
            return default_student_group

        # 3. Предзагрузка всех сессий (расписания)
        batch_ids = self.course_line_ids.mapped('batch_id').ids
        all_sessions = env['op.session'].search([('batch_id', 'in', batch_ids)])
        sessions_by_batch = {}
        for session in all_sessions:
            key = (session.batch_id.id, session.subject_id.id)
            sessions_by_batch.setdefault(key, env['op.session'])
            sessions_by_batch[key] |= session

        # 4. Собираем имена всех ожидаемых каналов для batch search
        expected_channel_names = set()
        if self.create_general_channel and self.general_channel_name:
            expected_channel_names.add(self.general_channel_name)

        for line in self.course_line_ids:
            ch_name = self._channel_name(line.batch_id)
            expected_channel_names.add(ch_name)
            for subject in line.subject_ids:
                expected_channel_names.add(f'{ch_name} — {subject.display_name}')

        # 5. Batch search существующих каналов
        existing_channels = env['discuss.channel'].search([
            ('name', 'in', list(expected_channel_names)),
            ('channel_type', '=', 'channel'),
        ])
        channel_pool = {ch.name: ch for ch in existing_channels}

        # 6. Подготавливаем данные для создания недостающих каналов
        channel_data = []  # list of dicts: name, description, class_group

        if self.create_general_channel:
            if not self.general_channel_name:
                raise UserError(_('Укажите имя общего канала.'))
            channel_data.append({
                'name': self.general_channel_name,
                'description': 'Общие объявления школы',
                'class_group': default_student_group,
            })

        for line in self.course_line_ids:
            batch = line.batch_id
            class_group = get_cached_class_group(batch.name)
            ch_name = self._channel_name(batch)

            channel_data.append({
                'name': ch_name,
                'description': f'Классный канал: {ch_name}',
                'class_group': class_group,
            })

            for subject in line.subject_ids:
                sub_name = f'{ch_name} — {subject.display_name}'
                channel_data.append({
                    'name': sub_name,
                    'description': f'Предмет: {subject.display_name} ({ch_name})',
                    'class_group': class_group,
                })

        # 7. Batch create недостающих каналов
        to_create = []
        for cd in channel_data:
            if cd['name'] not in channel_pool:
                vals = {
                    'name': cd['name'],
                    'description': cd['description'],
                    'channel_type': 'channel',
                }
                # group_ids: админы + класс-группа (для автоподписки)
                group_ids = list(admin_group_ids)
                if cd['class_group']:
                    vals['group_public_id'] = cd['class_group'].id
                    group_ids.append(cd['class_group'].id)
                if group_ids:
                    vals['group_ids'] = [fields.Command.set(group_ids)]
                to_create.append(vals)

        if to_create:
            new_channels = env['discuss.channel'].create(to_create)
            for ch in new_channels:
                channel_pool[ch.name] = ch

        # Обновляем ТОЛЬКО предварительно существующие каналы
        existing_channel_names = set(channel_pool.keys()) - {ch.name for ch in new_channels} if to_create else set(channel_pool.keys())

        for cd in channel_data:
            if cd['name'] not in existing_channel_names:
                continue  # Новый канал — уже создан с правильными значениями, обновлять не нужно
            ch = channel_pool.get(cd['name'])
            if ch:
                update_vals = {'description': cd['description']}
                if cd['class_group'] and ch.group_public_id != cd['class_group']:
                    update_vals['group_public_id'] = cd['class_group'].id
                # group_ids: админы + класс-группа
                group_ids = list(admin_group_ids)
                if cd['class_group']:
                    group_ids.append(cd['class_group'].id)
                if group_ids:
                    update_vals['group_ids'] = [fields.Command.set(group_ids)]
                ch.write(update_vals)

        # 8. Собираем участников для каждого канала (в памяти, без add_members)
        channel_partners = {ch.id: set() for ch in channel_pool.values()}
        general_channel_id = channel_pool.get(self.general_channel_name).id if self.create_general_channel else None
        all_class_partners = set()

        for line in self.course_line_ids:
            batch = line.batch_id
            ch_name = self._channel_name(batch)
            class_channel_id = channel_pool[ch_name].id

            # Безопасное получение partner_ids (фильтруем False)
            student_partner_ids = {p.id for p in line.student_ids.mapped('user_id.partner_id') if p}
            faculty_partner_ids = {p.id for p in line.faculty_ids.mapped('user_id.partner_id') if p}

            all_partners = student_partner_ids | faculty_partner_ids | admin_partner_ids
            all_class_partners |= all_partners

            channel_partners[class_channel_id] |= all_partners

            # Предметные каналы
            for subject in line.subject_ids:
                sub_name = f'{ch_name} — {subject.display_name}'
                subj_channel_id = channel_pool[sub_name].id

                sub_partners = admin_partner_ids.copy()
                sub_partners |= student_partner_ids
                sessions = sessions_by_batch.get((batch.id, subject.id), env['op.session'])
                sub_faculty = sessions.mapped('faculty_id') & line.faculty_ids
                sub_partners |= {p.id for p in sub_faculty.mapped('user_id.partner_id') if p}

                channel_partners[subj_channel_id] |= sub_partners

        # 9. Общий канал
        if general_channel_id:
            channel_partners[general_channel_id] = all_class_partners | admin_partner_ids

        # 10. Batch create discuss.channel.member (ГЛАВНОЕ УСКОРЕНИЕ)
        all_partner_ids = set()
        for pids in channel_partners.values():
            all_partner_ids |= pids

        all_channel_ids = list(channel_partners.keys())

        # Находим существующих участников ОДНИМ запросом
        existing_members = env['discuss.channel.member'].search([
            ('channel_id', 'in', all_channel_ids),
            ('partner_id', 'in', list(all_partner_ids)),
        ])
        existing_set = {(m.channel_id.id, m.partner_id.id) for m in existing_members}

        # Создаем недостающих ОДНИМ batch create
        members_to_create = []
        for channel_id, partner_ids in channel_partners.items():
            for partner_id in partner_ids:
                if (channel_id, partner_id) not in existing_set:
                    members_to_create.append({
                        'channel_id': channel_id,
                        'partner_id': partner_id,
                    })

        if members_to_create:
            env['discuss.channel.member'].create(members_to_create)

        created_counts = {
            'general': 1 if self.create_general_channel else 0,
            'class': len(self.course_line_ids),
            'subject': sum(len(line.subject_ids) for line in self.course_line_ids),
        }

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

    @api.depends('student_ids', 'faculty_ids', 'subject_ids')
    def _compute_counts(self):
        for line in self:
            line.student_count = len(line.student_ids)
            line.faculty_count = len(line.faculty_ids)
            line.subject_count = len(line.subject_ids)

