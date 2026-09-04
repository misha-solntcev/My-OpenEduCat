# -*- coding: utf-8 -*-
"""Персональная настройка колонок журнала урока (миниапп).

Хранится на res.users — настройка одна на учителя/админа для ВСЕХ журналов
(как согласовано в мокапе lesson-journal-columns.html, вариант B).
Оценка 1 и посещаемость — всегда видны, выключаемых колонок три:
О2 / О3 / Примечание. Дефолт: все выключены (О1 + Посещаемость).

Важно: res.users.write под самим собой разрешён только для полей из
SELF_WRITEABLE_FIELDS (Odoo 18) — без расширения список POST
/api/journal/columns падает с AccessError и тумблер откатывается.
"""
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    SELF_WRITEABLE_FIELDS = [
        'signature', 'action_id', 'image_1920', 'tz', 'name', 'email',
        'miniapp_show_grade_2', 'miniapp_show_grade_3', 'miniapp_show_note',
    ]

    miniapp_show_grade_2 = fields.Boolean("Миниапп: колонка Оценка 2")
    miniapp_show_grade_3 = fields.Boolean("Миниапп: колонка Оценка 3")
    miniapp_show_note = fields.Boolean("Миниапп: колонка Примечание")
