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
    )
    course_ids = fields.Many2many(
        'op.course',
        string='Курсы/Классы',
    )
    create_general_channel = fields.Boolean(
        string='Создать общий канал',
        default=True,
    )
    general_channel_name = fields.Char(
        string='Имя общего канала',
        default='Школа РОСТ',
    )
    course_line_ids = fields.One2many(
        'create.channel.wizard.course',
        'wizard_id',
        string='Классы/Потоки',
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
                [], order='id desc', limit=1)
        return year.id if year else None

    # ---------- line generation ----------

    def _batches_for_year(self, year_id, course_ids):
        """Возвращает op.batch для выбранного year И course_ids.

        Источник правды — связь ученика с year через op.student.course
        (OpStudentCourse.academic_years_id ↔ batch_id ↔ course_id).

        Почему НЕ batch.start_date: в базе есть batch с завышенной
        start_date (6 А (2025-2026) имеет start_date=2026-09-01),
        из‑за чего оба year попадают в одну выборку.

        Почему state='running': выпускники (11 класс, state='finished')
        за 2025-2026 НЕ должны попадать в 2026-2027 и наоборот — только
        активно обучающиеся студенты формируют batch-year.

        Никакого fallback на name: если за выбранный year нет зачисленных
        студентов (новый year ещё не начался), batch не возвращается —
        каналы создаются только для students, которых действительно
        зачисили в этот year.
        """
        domain = [('course_id', 'in', course_ids)]
        if not year_id:
            return self.env['op.batch'].search(domain, order='name asc')

        cd = self.env['op.student.course'].search([
            ('academic_years_id', '=', year_id),
            ('course_id', 'in', course_ids),
            ('state', '=', 'running'),
            ('batch_id', '!=', False),
        ], order='id')
        batch_ids = cd.mapped('batch_id').ids
        if batch_ids:
            domain += [('id', 'in', batch_ids)]
        else:
            # за этот year нет running студентов — пусто
            domain += [('id', 'in', [])]

        return self.env['op.batch'].search(domain, order='name asc')

    @api.model
    def _prepare_course_lines(self, course_ids, year_id=None):
        """Всегда начинается с Command.clear() — исключает дублирование
        строк в веб-клиенте (баг NewId при 2→4→8).

        Используется из action_create_channels, если onchange не сработал
        в UI (wizard открывается из Discuss без active_model=op.course).
        """
        courses = self.env['op.course'].browse(course_ids)
        if not courses:
            return [fields.Command.clear()]

        batches = self._batches_for_year(year_id, list(courses.ids))
        commands = [fields.Command.clear()]
        for batch in batches:
            commands.append(fields.Command.create({
                'academic_year_id': year_id,
                'course_id': batch.course_id.id,
                'batch_id': batch.id,
                'subject_ids': [fields.Command.set(
                    batch.course_id.subject_ids.ids)],
                'student_ids': [fields.Command.set(
                    self._students_for_batch(batch.id).ids)],
                'faculty_ids': [fields.Command.set(
                    self._faculty_for_batch(batch.id).ids)],
                'subscribe_students_to_subjects': True,
                'subscribe_teachers_to_subjects': True,
            }))
        return commands

    def _students_for_batch(self, batch_id):
        """Студенты batch с активными пользователями."""
        return self.env['op.student'].search([
            ('course_detail_ids.batch_id', '=', batch_id),
            ('user_id', '!=', False),
        ], order='id')

    def _faculty_for_batch(self, batch_id):
        """Преподаватели batch по его sessions."""
        return self.env['op.session'].search([
            ('batch_id', '=', batch_id),
        ]).mapped('faculty_id')

    def _rebuild_course_lines(self):
        """Полный пересбор строк: Command.clear() + новые. Используется
        в onchange и в action_create_channels."""
        year_id = self.academic_year_id.id if self.academic_year_id else None
        self.course_line_ids = self._prepare_course_lines(
            self.course_ids.ids, year_id)

    @api.onchange('academic_year_id', 'course_ids')
    def _onchange_academic_year_and_courses(self):
        """Пересобирает строки при изменении года или списка курсов."""
        self._rebuild_course_lines()

    # ---------- admin helpers ----------

    @api.model
    def _get_admin_groups_global(self):
        """Группы администраторов (back office)."""
        groups = self.env['res.groups']
        try:
            groups |= self.env.ref(
                'openeducat_core.group_op_back_office_admin')
        except ValueError:
            pass
        return groups

    @api.model
    def _get_admin_partners(self, admin_groups=None):
        """Партнёры администраторов."""
        if admin_groups is None:
            admin_groups = self._get_admin_groups_global()
        if not admin_groups:
            return self.env['res.partner']
        users = self.env['res.users'].search([
            ('groups_id', 'in', admin_groups.ids),
        ])
        return users.mapped('partner_id')

    # ---------- class group ----------

    def _get_class_group(self, batch):
        """Группа класса по номеру в имени batch ('10 А' →
        'Ученики 10 класс'). fallback → group_op_students."""
        match = re.match(r'^((\d+)', batch.name or '')
        if match:
            class_num = int(match.group(2))
            if 1 <= class_num <= 11:
                group_name = 'Ученики %d класс' % class_num
                group = self.env['res.groups'].search(
                    [('name', '=', group_name)], limit=1)
                if group:
                    return group
        return self.env.ref(
            'openeducat_core.group_op_students', raise_if_not_found=False)

    # ---------- channel helpers ----------

    def _all_groups(self, class_group, admin_groups):
        """Список Command.link для group_ids канала."""
        groups = [fields.Command.link(g.id) for g in admin_groups]
        if class_group:
            groups.append(fields.Command.link(class_group.id))
        return groups

    def _get_or_create_general_channel(self, admin_groups):
        """Create/get school-wide General channel."""
        channel = self.env['discuss.channel'].search([
            ('name', '=', self.general_channel_name),
            ('channel_type', '=', 'channel'),
        ], limit=1)
        student_group = self.env.ref(
            'openeducat_core.group_op_students', raise_if_not_found=False)
        all_groups = self._all_groups(student_group, admin_groups)
        if not channel:
            channel = self.env['discuss.channel'].create({
                'name': self.general_channel_name,
                'channel_type': 'channel',
                'description': 'Общие объявления для всей школы',
                'group_public_id': student_group.id if student_group else False,
                'group_ids': all_groups,
            })
        else:
            channel.write({'group_ids': all_groups})
        return channel

    def _get_or_create_channel(self, name, description, class_group,
                               admin_groups):
        """Универсальный поиск/создание канала по имени."""
        channel = self.env['discuss.channel'].search([
            ('name', '=', name),
            ('channel_type', '=', 'channel'),
        ], limit=1)
        all_groups = self._all_groups(class_group, admin_groups)
        if not channel:
            channel = self.env['discuss.channel'].create({
                'name': name,
                'channel_type': 'channel',
                'description': description,
                'group_public_id': class_group.id if class_group else False,
                'group_ids': all_groups,
            })
        else:
            channel.write({'group_ids': all_groups})
        return channel

    def _channel_name(self, batch):
        """Имя классного канала с суффиксом учебного года, если название
        batch не содержит его — чтобы каналы разных лет не пересекались."""
        year_name = self.academic_year_id.name if self.academic_year_id else ''
        if year_name and year_name not in (batch.name or ''):
            return '%s (%s)' % (batch.name, year_name)
        return batch.name

    # ---------- subscription ----------

    def _subscribe_partners(self, channel, partners):
        """Подписать партнёров на канал через штатный Discuss API.

        channel.add_members создаёт discuss.channel.member и обновляет
        channel_partner_ids — не нужно писать channel_partner_ids вручную
        (дублирование member-записей приводит к UniqueViolation)."""
        if not partners or not channel:
            return
        channel.add_members(partner_ids=partners.ids)

    # ---------- main action ----------

    def action_create_channels(self):
        """Создать каналы на основе выбора в wizard."""
        self.ensure_one()

        # Защита: если onchange не сработал в UI, но courses есть.
        if self.course_ids and not self.course_line_ids:
            self._rebuild_course_lines()

        if not self.course_line_ids and not self.create_general_channel:
            raise UserError(_(
                'Выберите учебный год и хотя бы один класс, либо включите '
                'создание общего канала.'))

        admin_groups = self._get_admin_groups_global()
        admin_partners = self._get_admin_partners(admin_groups)

        created = {'class': 0, 'subject': 0, 'general': 0}

        # 1. General school channel
        general_channel = None
        if self.create_general_channel:
            if not self.general_channel_name:
                raise UserError(_('Укажите имя общего канала.'))
            general_channel = self._get_or_create_general_channel(admin_groups)
            created['general'] = 1

        # 2. Классы и предметы
        for course_line in self.course_line_ids:
            batch = course_line.batch_id
            class_group = self._get_class_group(batch)
            ch_name = self._channel_name(batch)

            class_channel = self._get_or_create_channel(
                ch_name,
                'Классный канал для %s' % ch_name,
                class_group,
                admin_groups,
            )
            created['class'] += 1

            student_partners = course_line.student_ids.mapped('user_id.partner_id')
            faculty_partners = course_line.faculty_ids.mapped('user_id.partner_id')
            all_class_partners = student_partners | faculty_partners | admin_partners

            self._subscribe_partners(class_channel, all_class_partners)
            if general_channel:
                self._subscribe_partners(general_channel, all_class_partners)

            for subject in course_line.subject_ids:
                subject_channel = self._get_or_create_channel(
                    '%s — %s' % (ch_name, subject.display_name),
                    '%s — %s' % (subject.display_name, ch_name),
                    class_group,
                    admin_groups,
                )
                created['subject'] += 1

                sub_partners = self.env['res.partner']
                if course_line.subscribe_students_to_subjects:
                    sub_partners |= student_partners
                if course_line.subscribe_teachers_to_subjects:
                    subject_sessions = self.env['op.session'].search([
                        ('batch_id', '=', batch.id),
                        ('subject_id', '=', subject.id),
                    ])
                    subject_faculty = subject_sessions.mapped(
                        'faculty_id') & course_line.faculty_ids
                    sub_partners |= subject_faculty.mapped('user_id.partner_id')
                sub_partners |= admin_partners
                self._subscribe_partners(subject_channel, sub_partners)

        parts = []
        if created['class']:
            parts.append('%d классовых каналов' % created['class'])
        if created['subject']:
            parts.append('%d предметных каналов' % created['subject'])
        if created['general']:
            parts.append('1 общий канал')
        result_msg = 'Готово! Создано/обновлено: ' + ', '.join(parts) + '.'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Каналы созданы/обновлены',
                'message': result_msg,
                'type': 'success',
                'sticky': False,
            },
        }


class CreateChannelWizardCourse(models.TransientModel):
    _name = 'create.channel.wizard.course'
    _description = 'Course settings for channel creation'

    wizard_id = fields.Many2one(
        'create.channel.wizard', required=True, ondelete='cascade',
    )
    academic_year_id = fields.Many2one(
        'op.academic.year',
        string='Учебный год',
        required=True,
    )
    course_id = fields.Many2one(
        'op.course', string='Курс', required=True,
    )
    batch_id = fields.Many2one(
        'op.batch', string='Класс/Поток', required=True,
    )
    subject_ids = fields.Many2many(
        'op.subject', string='Предметы',
    )
    student_ids = fields.Many2many(
        'op.student', string='Ученики',
    )
    faculty_ids = fields.Many2many(
        'op.faculty', string='Учителя',
    )
    subscribe_students_to_subjects = fields.Boolean(
        string='Подписывать учеников на предметные каналы',
        default=True,
    )
    subscribe_teachers_to_subjects = fields.Boolean(
        string='Подписывать учителей на предметные каналы',
        default=True,
    )
