# -*- coding: utf-8 -*-
"""Фикс /web/image для моделей, у которых поле ``name`` — many2one.

База по умолчанию берёт имя файла из поля ``name``
(``_get_filename_from_record``), считая его Char: у op.parent это
res.partner-запись, и ``_get_stream_from`` падает на
``recordset.replace()`` → AttributeError → 500 на ЛЮБОМ
/web/image/op.parent/<id>/<field> (канбан, форма, прямая ссылка).

Чинится здесь, а не своим полем-копией фото: изображение родителя —
это изображение контакта (как у ученика и учителя, которые делегируют
res.partner через _inherits), и второй копии байтов быть не должно.
Пустой display_name база сама заменяет на ``<table>-<id>-<field>``.
"""
from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _get_image_stream_from(self, record, *args, **kwargs):
        name_field = record._fields.get('name')
        if (name_field is not None and name_field.type == 'many2one'
                # только когда вызывающий не задал ни имя файла, ни поле
                and kwargs.get('filename_field', 'name') == 'name'
                and not kwargs.get('filename')):
            kwargs['filename_field'] = 'display_name'
        return super()._get_image_stream_from(record, *args, **kwargs)
