import re

from odoo import api, fields, models


class RostChannelGroups(models.AbstractModel):
    """Группы доступа к каналам Discuss: единая логика для мастера
    (create.channel.wizard) и автосинхронизации при зачислении ученика.

    Имена групп — соглашение, на которое завязаны каналы:
      «Участники каналов N класса»  — доступ к классному каналу;
      «Канал N класс — <Предмет>»   — доступ к предметному каналу.

    Это НЕ ролевые группы (Админы / Учителя / Ученики — те три, что в
    коде с xmlid). Это группы доступа к каналам: у каждого канала
    group_public_id ссылается на одну из них, и по ней Odoo решает,
    кому канал видно (rule 42). Создаёт их мастер create.channel.wizard,
    поэтому xmlid у них нет — ищем по имени.

    Импликаций у них нет намеренно: добавление учителя в «Участники
    каналов» не должно тянуть роль Student (rule 613 режет тогда
    библиотечные карточки).
    """
    _name = 'rost.channel.groups'
    _description = 'Группы доступа к каналам Discuss'

    # ---------- имена и номера классов ----------

    @api.model
    def _class_num(self, batch_name):
        """Номер класса из имени батча ('11 А  2026/2027' -> '11').

        None, если номер не распознан или вне диапазона 1..11 — тогда
        группа доступа не подбирается.
        """
        match = re.match(r'^(\d+)', batch_name or '')
        if not match:
            return None
        num = int(match.group(1))
        return num if 1 <= num <= 11 else None

    @staticmethod
    def _channel_group_name(class_num):
        return f'Участники каналов {class_num} класса'

    @staticmethod
    def _subject_group_name(class_num, subject):
        return f'Канал {class_num} класс — {subject.display_name}'

    @staticmethod
    def _subject_channel_name(batch_name, subject):
        """Имя предметного канала — как у мастера: '<класс> — <предмет>'."""
        return f'{batch_name} — {subject.display_name}'

    @staticmethod
    def _is_channel_group(group):
        """Похоже ли имя группы на одну из наших (для снятия устаревших)."""
        name = group.name or ''
        return name.startswith('Участники каналов ') or name.startswith('Канал ')

    # ---------- группы ----------

    @api.model
    def _get_or_create_channel_group(self, class_num):
        """«Участники каналов N класса» — ученики + учителя класса."""
        name = self._channel_group_name(class_num)
        group = self.env['res.groups'].sudo().search([('name', '=', name)], limit=1)
        if not group:
            group = self.env['res.groups'].sudo().create({'name': name})
        return group

    @api.model
    def _get_or_create_subject_group(self, class_num, subject):
        """«Канал N класс — Предмет» — записанные на предмет + его учителя."""
        name = self._subject_group_name(class_num, subject)
        group = self.env['res.groups'].sudo().search([('name', '=', name)], limit=1)
        if not group:
            group = self.env['res.groups'].sudo().create({'name': name})
        return group

    # ---------- синхронизация одного ученика ----------

    def _student_targets(self):
        """[(group, channel_name)] — группы и каналы ученика self.

        Предметы берём из subject_ids зачисления. Если предметы не
        заполнены (старые классы) — fallback на предметы курса, как в
        мастере: лучше дать каналы лишнему, чем не дать никому.
        """
        self.ensure_one()
        targets = []
        enrolments = self.course_detail_ids.filtered(
            lambda d: d.state == 'running' and d.batch_id)
        for enrolment in enrolments:
            batch = enrolment.batch_id
            class_num = self._class_num(batch.name)
            if not class_num:
                continue
            targets.append((
                self._get_or_create_channel_group(class_num),
                batch.name,
            ))
            subjects = enrolment.subject_ids or batch.course_id.subject_ids
            for subject in subjects:
                targets.append((
                    self._get_or_create_subject_group(class_num, subject),
                    self._subject_channel_name(batch.name, subject),
                ))
        return targets

    def sync_student_channels(self):
        """Привести членство ученика в каналах к его классу.

        Вызывается при зачислении и при смене класса/предметов.
        Идемпотентна: добавляет недостающее, снимает устаревшее.
        Каналы, которых ещё нет (мастер не прогоняли), пропускает —
        их создаст мастер, опираясь на уже готовые группы.
        """
        self.ensure_one()
        if not self.user_id or not self.user_id.partner_id:
            return
        self = self.sudo()
        user = self.user_id

        targets = self._student_targets()
        target_groups = self.env['res.groups']
        for group, _channel_name in targets:
            target_groups |= group

        missing = target_groups - user.groups_id
        if missing:
            user.write({'groups_id': [(4, g.id) for g in missing]})

        # Устаревшее: группы классов, в которых ученик больше не
        # учится (перевод/отчисление). Снимаем ТОЛЬКО этого юзера —
        # учителя в той же группе остаются. Админов не трогаем.
        admin_group = self.env.ref(
            'openeducat_core.group_op_back_office_admin', raise_if_not_found=False)
        if not (admin_group and user in admin_group.users):
            stale = user.groups_id.filtered(
                lambda g: g.id not in target_groups.ids
                and self.env['rost.channel.groups']._is_channel_group(g))
            for group in stale:
                group.write({'users': [fields.Command.unlink(user.id)]})

        self._sync_channel_members(targets)

    def _sync_channel_members(self, targets):
        """Добавить партнёра в каналы, к которым он теперь имеет доступ.

        Только добавление: классные каналы мастер тоже не чистит (там
        ручные добавления завучу терять нельзя), а предметные каналы
        пересобирает целиком он сам — тут мы лишь добиваем новичка.
        """
        if not targets:
            return
        names = {channel_name for _group, channel_name in targets}
        channels = self.env['discuss.channel'].sudo().search([
            ('name', 'in', list(names)),
            ('channel_type', '=', 'channel'),
        ])
        if not channels:
            return
        partner = self.user_id.partner_id
        existing = self.env['discuss.channel.member'].sudo().search([
            ('channel_id', 'in', channels.ids),
            ('partner_id', '=', partner.id),
        ])
        have = set(existing.mapped('channel_id').ids)
        todo = [fields.Command.create({
            'channel_id': c.id,
            'partner_id': partner.id,
        }) for c in channels if c.id not in have]
        if todo:
            self.env['discuss.channel.member'].sudo().create(todo)
