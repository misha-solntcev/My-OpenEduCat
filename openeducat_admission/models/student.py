# -*- coding: utf-8 -*-
"""Аккаунт ученика: транзишн «почта появилась позже» и предупреждение.

Модель аккаунтов (решение 12.11.2026):
- у ребёнка нет своей почты — аккаунт один, родительский (мама);
- почта появилась (перешёл в старшую школу или иначе) — секретарь
  заполняет «Email ученика» и создаёт юзер кнопкой; повторное письмо,
  если ссылка не активировали — кнопка «Отправить приглашение повторно».
"""
import re

from odoo import _
from odoo import api, fields, models
from odoo.exceptions import UserError


class OpStudent(models.Model):
    _inherit = 'op.student'

    rost_no_email_alert = fields.Boolean(
        'Старшие классы без email (предупреждение)',
        compute='_compute_rost_no_email_alert')
    rost_email_in_contact = fields.Boolean(
        'Почта только в контакте (подсказка)',
        compute='_compute_rost_no_email_alert')

    @api.depends('email', 'user_id', 'partner_id.email', 'course_detail_ids')
    def _compute_rost_no_email_alert(self):
        """Предупреждать только тогда, когда аккаунт ДЕЙСТВИТЕЛЬНО не создать.

        Почты может не быть в op.student.email, но быть в контакте
        (res.partner) — апстрим держит на op.student собственное поле
        Email, а у учеников старше 13.11.2026 почта лежит в контакте.
        Раньше условие смотрело только на своё поле и не смотрело на
        user_id: баннер «аккаунт создать нельзя» показывался 107 ученикам,
        у которых аккаунт уже был (13.11.2026, Барановская Т.).
        """
        for student in self:
            grade = student._rost_grade_number()
            senior = bool(grade and grade >= 5)
            own = (student.email or '').strip()
            contact = (student.partner_id.email or '').strip()
            no_account = not student.user_id
            student.rost_no_email_alert = bool(
                senior and no_account and not own and not contact)
            student.rost_email_in_contact = bool(
                senior and no_account and not own and contact)

    def _rost_grade_number(self):
        """Номер параллели из имени батча/курса зачисления
        («5 А  2026/2027» → 5). У op.student нет batch_id — батч живёт
        в course_detail_ids (op.student.course)."""
        self.ensure_one()
        details = self.course_detail_ids.sorted(
            lambda d: 0 if d.state == 'running' else 1)
        for detail in details:
            for name in (detail.batch_id.name, detail.course_id.name):
                match = re.match(r'\s*(\d+)', name or '')
                if match:
                    return int(match.group(1))
        return 0

    def _rost_login_taken(self, login):
        """Чужой юзер с таким логином — см. res.users._rost_login_taken."""
        return self.env['res.users']._rost_login_taken(login)

    def _rost_create_student_user(self, email, send_invite=True,
                                  invite_raise=False):
        """Ядро транзишна: юзер ученика на его собственной почте.

        Порядок важен: сначала родительский юзер (если его нет), потом
        write(user_id) — тогда openededucat_parent сам допишет ребёнка
        в child_ids родителя (models/parent.py, ветка vals['user_id']).
        invite_raise: True для кнопок (секретарь должен увидеть сбой
        SMTP), False для зачисления — письмо не роняет enroll.
        """
        self.ensure_one()
        email = (email or '').strip()
        if not email:
            raise UserError(_(
                'У ученика «%s» не заполнен «Email ученика» — '
                'запросите почту у семьи.') % self.name)
        taken = self._rost_login_taken(email)
        if taken:
            raise UserError(_(
                'Логин «%s» уже занят (пользователь «%s»). '
                'Запросите у семьи другой адрес.') % (email, taken.name))
        parent = self.parent_ids[:1]
        if parent and parent.partner_id and parent.partner_id.email \
                and not parent.user_id and not parent.partner_id.user_ids:
            parent.create_parent_user()
            if send_invite:
                parent.user_id.sudo()._rost_send_invite(
                    'parent', raise_failure=not invite_raise)
        user = self.env['res.users'].sudo().create({
            'name': self.name,
            'login': email,
            'email': email,
            'image_1920': self.image_1920 or False,
            'is_student': True,
            'company_id': self.company_id.id,
            'company_ids': [(6, 0, [self.company_id.id])],
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('openeducat_core.group_op_students').id])],
        })
        self.write({'email': email, 'user_id': user.id})
        if send_invite:
            user.sudo()._rost_send_invite(
                'student', raise_failure=not invite_raise)
        return user

    def action_rost_create_account(self):
        """Кнопка «Создать аккаунт и отправить приглашение» (транзишн)."""
        self.ensure_one()
        if self.user_id:
            raise UserError(_(
                'У ученика уже есть аккаунт (логин %s).') % self.user_id.login)
        user = self._rost_create_student_user(
            self.email, send_invite=True, invite_raise=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Аккаунт создан'),
                'message': _('Приглашение отправлено на %s. '
                             'Ссылка действует 24 часа.') % user.login,
                'sticky': False,
            },
        }

    def action_rost_resend_invite(self):
        """Повторное письмо: ученику (юзер есть) или родителю (режим А)."""
        self.ensure_one()
        if self.user_id:
            target = self.user_id
            kind = 'student'
        else:
            parent = self.parent_ids[:1]
            target = parent.user_id if parent else False
            if not target:
                raise UserError(_(
                    'Нечего отправлять: у ученика нет аккаунта, '
                    'а у родителя нет аккаунта на его почте.'))
            kind = 'parent'
        target.sudo()._rost_send_invite(kind)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Приглашение отправлено'),
                'message': _('Повторное письмо ушло на %s. '
                             'Ссылка действует 24 часа.') % target.login,
                'sticky': False,
            },
        }
