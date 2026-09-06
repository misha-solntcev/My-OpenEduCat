# -*- coding: utf-8 -*-
# Одноразовые токены на скачивание вложений сдачи ДЗ (миниапп).
# Зачем: ir.attachment ученика нельзя отдавать по /web/content напрямую
# (access token глобален и вечен), а teacher читает сдачи через sudo-API.
# Токен: secrets.token_urlsafe, живёт 24 ч, привязан к конкретному
# вложению. Просроченные чистятся при каждом создании.
import secrets
from datetime import datetime, timedelta

from odoo import api, fields, models


class HwAttachmentToken(models.Model):
    _name = 'hw.attachment.token'
    _description = 'Одноразовый токен на скачивание вложения ДЗ'

    token = fields.Char(required=True, index=True)
    attachment_id = fields.Many2one(
        'ir.attachment', required=True, ondelete='cascade')
    created_at = fields.Datetime(default=fields.Datetime.now, required=True)

    TTL_HOURS = 24

    @api.model_create_multi
    def create(self, vals_list):
        # Чистим просроченные (дёшево: раз в создание, таблица крошечная —
        # токены живут сутки).
        self.search([
            ('created_at', '<',
             fields.Datetime.now() - timedelta(hours=self.TTL_HOURS)),
        ]).unlink()
        for vals in vals_list:
            vals.setdefault('token', secrets.token_urlsafe(32))
            vals.setdefault('created_at', fields.Datetime.now())
        return super().create(vals_list)

    def get_valid(self, token):
        """Вложение по живому токену или None (токен истёк/неизвестен)."""
        rec = self.search([('token', '=', token)], limit=1)
        if not rec:
            return None
        created = rec.created_at
        if isinstance(created, str):
            created = fields.Datetime.from_string(created)
        if datetime.now() - created > timedelta(hours=self.TTL_HOURS):
            rec.unlink()
            return None
        return rec.attachment_id
