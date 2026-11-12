# -*- coding: utf-8 -*-
"""Приглашения в учебные аккаунты (Школа РОСТ).

Ядровое action_reset_password шлёт письмо с темой «Сброс пароля»,
адресованное имени пользователя: родитель получает «Дорогой <ФИО ребёнка>,
был запрошен сброс пароля» без всякого запроса — выглядит как взлом.
Вместо него — свои шаблоны (parent/student) с внятным текстом.
"""
from odoo import _
from odoo import api, models
from odoo.exceptions import UserError

INVITE_TEMPLATES = {
    'parent': 'openeducat_admission.mail_template_rost_invite_parent',
    'student': 'openeducat_admission.mail_template_rost_invite_student',
}


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _rost_login_taken(self, login):
        """Чужой юзер с таким логином, включая архивных: unique-констрейнт
        на res.users.login не смотрит на active (кейс egarbst@gmail.com,
        приёмки #1593/#1588 — падение зачисления второго ребёнка)."""
        return self.with_context(active_test=False).search(
            [('login', '=', login)], limit=1)

    def _rost_send_invite(self, kind='student', raise_failure=True):
        """Одноразовая ссылка установки пароля + письмо «Аккаунт ...».

        Тело рендерим inline-движком и создаём mail.mail вручную (как
        ядро для reset_password_email): mail.template в Odoo 18 рендерит
        body_html qweb-движком, который в «regex-режиме» не отрабатывает
        динамический URL в атрибуте href — письмо уходило с буквальными
        {{ ... }}. Inline-движок (проверено 12.11.2026) отрабатывает
        {{ object.partner_id._get_signup_url() }} целиком.

        kind: 'parent' | 'student' — выбор шаблона.
        raise_failure=False — не ронять зачисление при сбое SMTP:
        аккаунт уже создан, письмо повторяется кнопкой
        «Отправить приглашение повторно» на карточке ученика.
        """
        self.ensure_one()
        if not self.email:
            raise UserError(_(
                'Нельзя отправить приглашение: у пользователя %s нет email.')
                % self.name)
        self.partner_id.signup_prepare(signup_type='signup')
        template = self.env.ref(INVITE_TEMPLATES[kind])
        mixin = self.env['mail.render.mixin'].with_context(
            lang=self.lang or self.env.lang)
        try:
            rendered = mixin._render_template(
                template.body_html, 'res.users', self.ids,
                engine='inline_template', options={'post_process': True})
            subject = mixin._render_template(
                template.subject, 'res.users', self.ids,
                engine='inline_template')
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject[self.id],
                'body_html': rendered[self.id],
                'email_from':
                    self.company_id.email_formatted or self.email_formatted,
                'email_to': self.email_formatted,
                'auto_delete': True,
            })
            mail.send()
        except Exception:
            if raise_failure:
                raise
            return False
        return True
