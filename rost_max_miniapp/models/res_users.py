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

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'miniapp_show_grade_2', 'miniapp_show_hw_1', 'miniapp_show_hw_2',
            'miniapp_show_note',
        ]

    miniapp_show_grade_2 = fields.Boolean("Миниапп: колонка Оценка 2")
    # ДЗ-колонки по умолчанию включены (требование: оценки за ДЗ видны в журнале).
    miniapp_show_hw_1 = fields.Boolean("Миниапп: колонка ДЗ 1", default=True)
    miniapp_show_hw_2 = fields.Boolean("Миниапп: колонка ДЗ 2", default=True)
    miniapp_show_note = fields.Boolean("Миниапп: колонка Примечание")
