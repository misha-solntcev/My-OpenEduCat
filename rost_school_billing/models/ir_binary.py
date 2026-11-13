# -*- coding: utf-8 -*-
"""Фикс /web/image для моделей с many2one-полем 'name' (op.parent).

Дефолт filename_field='name' в _get_image_stream_from у op.parent
возвращает res.partner-запись вместо строки → AttributeError на
.replace() → 500 → канбан показывает placeholder вместо аватара.
Для таких моделей имя файла берём из display_name (решение 12.11.2026).
"""
from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _get_image_stream_from(self, record, *args, **kwargs):
        name_field = record._fields.get('name')
        if name_field is not None and name_field.type == 'many2one':
            kwargs['filename_field'] = 'display_name'
        return super()._get_image_stream_from(record, *args, **kwargs)
