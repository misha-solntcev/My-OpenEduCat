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

        # Админы для вывода в отдельную колонку (res.users)
        admin_users = self._get_admin_users()

        commands = [fields.Command.clear()]

        for batch in batches:
            if not batch:
                continue
            batch_enrollments = enrollments_by_batch.get(batch.id, self.env['op.student.course'])
            students = batch_enrollments.mapped('student_id').filtered(lambda s: s.user_id)

            # Берем сессии из кэша, а не из БД
            batch_sessions = sessions_by_batch.get(batch.id, self.env['op.session'])
            faculty = (batch_sessions.mapped('faculty_id') | batch.homeroom_faculty_ids).filtered(lambda f: f.user_id)

            commands.append(fields.Command.create({
                'academic_year_id': self.academic_year_id.id,
                'course_id': batch.course_id.id,
                'batch_id': batch.id,
                'subject_ids': [fields.Command.set(batch.course_id.subject_ids.ids)],
                'student_ids': [fields.Command.set(students.ids)],
                'faculty_ids': [fields.Command.set(faculty.ids)],
                'admin_ids': [fields.Command.set(
                    (admin_users | batch.homeroom_faculty_ids.mapped('user_id')).ids)],
            }))

        self.course_line_ids = commands

    @api.onchange('academic_year_id', 'course_ids')
    def _onchange_academic_year_and_courses(self):
        """Пересобирает строки при изменении года или списка курсов."""
        self._rebuild_course_lines()

    # ---------- admin helpers ----------

    @api.model
    def _get_admin_users(self):
        """Возвращает пользователей с группой group_op_back_office_admin."""
        admin_group = self.env.ref('openeducat_core.group_op_back_office_admin', raise_if_not_found=False)
        if not admin_group:
            return self.env['res.users']
        return self.env['res.users'].search([('groups_id', 'in', admin_group.ids)])

    @api.model
    def _get_admin_partners(self):
        return self._get_admin_users().mapped('partner_id')

    # ---------- channel helpers ----------

    def _channel_name(self, batch):
        return batch.name if batch else 'Без класса'

    @staticmethod
    def _subject_channel_name(class_name, subject):
        """Единый формат имени предметного канала."""
        return f'{class_name} — {subject.display_name}'

    # ---------- helpers ----------

    def _partner_ids(self, records):
        """Извлекает partner_id из записей через user_id. Единая точка вместо копий."""
        return {p.id for p in records.mapped('user_id.partner_id') if p}

    def _validate_faculty_users(self):
        """Проверяет, у всех учителей в строках есть связанный пользователь.
        Выбрасывает UserError со списком имен, если есть учителя без user_id."""
        for line in self.course_line_ids:
            without_user = line.faculty_ids.filtered(lambda f: not f.user_id)
            if without_user:
                raise UserError(_(
                    'У следующих учителей нет связанного пользователя Odoo: %s. '
                    'Создайте пользователя в карточке учителя и повторите.'
                ) % ', '.join(without_user.mapped('name')))

    # ---------- action_create_channels sub-methods ----------

    def _prepare_context(self):
        """Возвращает self с отключенным трекингом/mail для массовых операций."""
        return self.with_context(
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
            mail_auto_subscribe=False,
        )

    def _validate_input(self):
        """Проверка: есть строки или общий канал."""
        if not self.course_line_ids and not self.create_general_channel:
            raise UserError(_('Выберите учебный год и хотя бы один класс, либо создайте общий канал.'))

    def _load_admin_data(self):
        """Возвращает (admin_partner_ids, admin_group_ids)."""
        admin_partner_ids = set(self._get_admin_partners().ids)
        admin_group = self.env.ref('openeducat_core.group_op_back_office_admin', raise_if_not_found=False)
        admin_group_ids = [admin_group.id] if admin_group else []
        return admin_partner_ids, admin_group_ids

    def _load_class_groups(self):
        """Возвращает (class_group_cache, default_student_group, get_cached_class_group_fn)."""
        class_groups_records = self.env['res.groups'].search([('name', '=like', 'Ученики % класс')])
        class_group_cache = {g.name: g for g in class_groups_records}
        default_student_group = self.env.ref('openeducat_core.group_op_students', raise_if_not_found=False)

        def get_cached_class_group(batch_name):
            match = re.match(r'^(\d+)', batch_name or '')
            if match:
                num = int(match.group(1))
                if 1 <= num <= 11:
                    name_key = f'Ученики {num} класс'
                    if name_key in class_group_cache:
                        return class_group_cache[name_key]
            return default_student_group

        return class_group_cache, default_student_group, get_cached_class_group

    def _get_or_create_channel_group(self, class_num):
        """Группа доступа к каналам класса «Участники каналов N класса».

        Отдельная от «Ученики N класс»: у каналов group_public_id указывает
        именно на неё, а в ней состоят ВСЕ участники канала (ученики +
        учителя). Импликаций у группы нет — добавление учителя не должно
        тянуть Student (иначе rule 613 режет ему библиотечные карточки).
        """
        name = f'Участники каналов {class_num} класса'
        group = self.env['res.groups'].search([('name', '=', name)], limit=1)
        if not group:
            group = self.env['res.groups'].create({
                'name': name,
            })
        return group

    def _get_channel_group_for_batch(self, batch_name):
        match = re.match(r'^(\d+)', batch_name or '')
        if not match:
            return self.env['res.groups']
        num = int(match.group(1))
        if not 1 <= num <= 11:
            return self.env['res.groups']
        return self._get_or_create_channel_group(num)

    def _load_sessions_cache(self):
        """Возвращает sessions_by_batch: {(batch_id, subject_id): op.session recordset}."""
        batch_ids = self.course_line_ids.mapped('batch_id').ids
        all_sessions = self.env['op.session'].search([('batch_id', 'in', batch_ids)])
        sessions_by_batch = {}
        for session in all_sessions:
            key = (session.batch_id.id, session.subject_id.id)
            sessions_by_batch.setdefault(key, self.env['op.session'])
            sessions_by_batch[key] |= session
        return sessions_by_batch

    def _build_channel_data(self, get_cached_class_group, default_student_group):
        """Строит channel_data + channel_pool (существующие каналы по ожидаемым именам)."""
        expected_channel_names = set()
        if self.create_general_channel and self.general_channel_name:
            expected_channel_names.add(self.general_channel_name)

        for line in self.course_line_ids:
            ch_name = self._channel_name(line.batch_id)
            expected_channel_names.add(ch_name)
            for subject in line.subject_ids:
                expected_channel_names.add(self._subject_channel_name(ch_name, subject))

        existing_channels = self.env['discuss.channel'].search([
            ('name', 'in', list(expected_channel_names)),
            ('channel_type', '=', 'channel'),
        ])
        channel_pool = {ch.name: ch for ch in existing_channels}

        channel_data = []
        if self.create_general_channel:
            if not self.general_channel_name:
                raise UserError(_('Укажите имя общего канала.'))
            channel_data.append({
                'name': self.general_channel_name,
                'description': 'Общие объявления школы',
                # group_public_id = Внутренний пользователь: канал видят все
                # internal-пользователи, включая учителей без роли Student.
                'class_group': self.env.ref('base.group_user', raise_if_not_found=False),
            })

        for line in self.course_line_ids:
            batch = line.batch_id
            # Группа доступа «Участники каналов N класса» вместо «Ученики N класс»:
            # у teacher-юзеров не должен появляться Student (rule 613 режет карточки).
            class_group = self._get_channel_group_for_batch(batch.name) or get_cached_class_group(batch.name)
            ch_name = self._channel_name(batch)

            channel_data.append({
                'name': ch_name,
                'description': f'Классный канал: {ch_name}',
                'class_group': class_group,
            })

            for subject in line.subject_ids:
                channel_data.append({
                    'name': self._subject_channel_name(ch_name, subject),
                    'description': f'Предмет: {subject.display_name} ({ch_name})',
                    'class_group': class_group,
                })

        return channel_data, channel_pool

    @staticmethod
    def _channel_create_vals(cd, admin_group_ids):
        """Vals для создания канала из элемента channel_data."""
        vals = {
            'name': cd['name'],
            'description': cd['description'],
            'channel_type': 'channel',
        }
        group_ids = list(admin_group_ids)
        if cd['class_group']:
            vals['group_public_id'] = cd['class_group'].id
            group_ids.append(cd['class_group'].id)
        if group_ids:
            vals['group_ids'] = [fields.Command.set(group_ids)]
        return vals

    def _create_new_channels(self, channel_data, channel_pool, admin_group_ids):
        """Batch create недостающих каналов. Обновляет и возвращает channel_pool."""
        to_create = [
            self._channel_create_vals(cd, admin_group_ids)
            for cd in channel_data if cd['name'] not in channel_pool
        ]
        new_channels = self.env['discuss.channel'].create(to_create) if to_create else self.env['discuss.channel']
        for ch in new_channels:
            channel_pool[ch.name] = ch
        return channel_pool

    def _update_existing_channels(self, channel_data, channel_pool, admin_group_ids):
        """Синхронизирует description/group_public_id/group_ids у существующих каналов."""
        for cd in channel_data:
            ch = channel_pool.get(cd['name'])
            if not ch:
                continue
            update_vals = {'description': cd['description']}
            if cd['class_group'] and ch.group_public_id != cd['class_group']:
                update_vals['group_public_id'] = cd['class_group'].id
            group_ids = list(admin_group_ids)
            if cd['class_group']:
                group_ids.append(cd['class_group'].id)
            if group_ids:
                update_vals['group_ids'] = [fields.Command.set(group_ids)]
            ch.write(update_vals)

    def _compute_channel_partners(self, channel_pool, sessions_by_batch, admin_partner_ids, get_cached_class_group):
        """Возвращает dict: {channel_id: set(partner_ids)}."""
        # Валидация учителей выполняется явно в action_create_channels
        channel_partners = {ch.id: set() for ch in channel_pool.values()}
        general_channel_id = channel_pool.get(self.general_channel_name).id if self.create_general_channel else None
        all_class_partners = set()

        for line in self.course_line_ids:
            batch = line.batch_id
            ch_name = self._channel_name(batch)
            class_channel_id = channel_pool[ch_name].id

            student_partner_ids = self._partner_ids(line.student_ids)
            faculty_partner_ids = self._partner_ids(line.faculty_ids)
            all_partners = student_partner_ids | faculty_partner_ids | admin_partner_ids
            all_class_partners |= all_partners

            channel_partners[class_channel_id] |= all_partners

            for subject in line.subject_ids:
                sub_name = self._subject_channel_name(ch_name, subject)
                subj_channel_id = channel_pool[sub_name].id

                sub_partners = admin_partner_ids.copy()
                sub_partners |= student_partner_ids
                # Учителя предмета (по расписанию) + классные руководители этого класса
                sessions = sessions_by_batch.get((batch.id, subject.id), self.env['op.session'])
                sub_faculty = sessions.mapped('faculty_id') | batch.homeroom_faculty_ids
                sub_partners |= self._partner_ids(sub_faculty & line.faculty_ids)

                channel_partners[subj_channel_id] |= sub_partners

        if general_channel_id:
            channel_partners[general_channel_id] = all_class_partners | admin_partner_ids

        return channel_partners

    def _sync_channel_members(self, channel_partners):
        """Batch create недостающих discuss.channel.member."""
        all_partner_ids = set()
        for pids in channel_partners.values():
            all_partner_ids |= pids
        all_channel_ids = list(channel_partners.keys())

        existing_members = self.env['discuss.channel.member'].search([
            ('channel_id', 'in', all_channel_ids),
            ('partner_id', 'in', list(all_partner_ids)),
        ])
        existing_set = {(m.channel_id.id, m.partner_id.id) for m in existing_members}

        members_to_create = []
        for channel_id, partner_ids in channel_partners.items():
            for partner_id in partner_ids:
                if (channel_id, partner_id) not in existing_set:
                    members_to_create.append({
                        'channel_id': channel_id,
                        'partner_id': partner_id,
                    })

        if members_to_create:
            self.env['discuss.channel.member'].create(members_to_create)

    def _sync_faculty_class_groups(self, get_cached_class_group):
        """Добавляет ВСЕМ участникам каналов группы «Участники каналов N класса».

        Видимость канала (Rule 42) определяется по group_public_id, а не по
        членству, поэтому в группу доступа должны входить и ученики, и
        учителя. Группа создается без импликаций — teacher-юзер не получает
        Student (rule 613 иначе режет библиотечные карточки: 0 AND all = 0).
        """
        for line in self.course_line_ids:
            class_group = self._get_channel_group_for_batch(line.batch_id.name)
            if not class_group:
                continue
            # ученики класса
            users = line.student_ids.filtered(lambda s: s.user_id).mapped('user_id')
            # учителя класса
            users |= line.faculty_ids.filtered(lambda f: f.user_id).mapped('user_id')
            for user in users:
                if class_group not in user.groups_id:
                    user.write({'groups_id': [fields.Command.link(class_group.id)]})

    def _build_result_notification(self):
        """Возвращает display_notification с количеством обработанных каналов."""
        created_counts = {
            'general': 1 if self.create_general_channel else 0,
            'class': len(self.course_line_ids),
            'subject': sum(len(line.subject_ids) for line in self.course_line_ids),
        }
        parts = [f'{count} {label}' for label, count in [
            ('общий', created_counts['general']),
            ('классных', created_counts['class']),
            ('предметных', created_counts['subject']),
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

    # ---------- main action ----------

    def action_create_channels(self):
        self.ensure_one()
        self = self._prepare_context()

        self._validate_input()
        self._validate_faculty_users()

        admin_partner_ids, admin_group_ids = self._load_admin_data()
        _, default_student_group, get_cached_class_group = self._load_class_groups()
        sessions_by_batch = self._load_sessions_cache()

        channel_data, channel_pool = self._build_channel_data(get_cached_class_group, default_student_group)
        channel_pool = self._create_new_channels(channel_data, channel_pool, admin_group_ids)
        self._update_existing_channels(channel_data, channel_pool, admin_group_ids)

        channel_partners = self._compute_channel_partners(
            channel_pool, sessions_by_batch, admin_partner_ids, get_cached_class_group
        )
        self._sync_channel_members(channel_partners)
        self._sync_faculty_class_groups(get_cached_class_group)

        return self._build_result_notification()


class CreateChannelWizardCourse(models.TransientModel):
    _name = 'create.channel.wizard.course'
    _description = 'Course line for channel creation'

    wizard_id = fields.Many2one('create.channel.wizard', required=True, ondelete='cascade')
    academic_year_id = fields.Many2one('op.academic.year', string='Учебный год', readonly=True)
    course_id = fields.Many2one('op.course', string='Курс', readonly=True)
    batch_id = fields.Many2one('op.batch', string='Класс/Поток', readonly=True)
    subject_ids = fields.Many2many('op.subject', string='Предметы', readonly=False)
    student_ids = fields.Many2many('op.student', string='Ученики', readonly=False)
    faculty_ids = fields.Many2many('op.faculty', string='Учителя', readonly=False)
    admin_ids = fields.Many2many('res.users', string='Админы', readonly=True)

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