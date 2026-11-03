# -*- coding: utf-8 -*-
# res.partner: ученикам запрещено менять СЕБЕ имя, email и фото (аватар).
#
# Зачем отдельный гейт, если уже есть write-гейт в res.users:
#  - res.users.name/email — related-поля на partner_id (base/models/res_users.py:408),
#    но запись идёт через res.partner.write(), если поле меняют на контакте;
#  - портал /my/account (portal/controllers/portal.py, route auth='user') правит
#    контакт так: partner.sudo().write(values) — мимо res.users.write вообще.
#    Т.е. ученик через страницу «Details» портала мог поменять себе имя/email.
#
# Почему нельзя проверять self.env.su:
#  - портал пишет именно через sudo(), поэтому env.su здесь True и признак
#    «пришло от доверенного кода» не различает портал и cron;
#  - различитель — env.uid: портал работает в контексте самого ученика
#    (uid = ученик), а cron/импорты/админские действия идут от uid 1/админа.
#    Поэтому условие: uid — ученик (без родителей и erp_manager) И пишем ровно
#    его собственный контакт.
#
# Изменение, а не факт: правка адреса/телефона через портал остаётся
# возможной. Портал шлёт в POST обязательные name/email ВСЕГДА (даже если
# ученик менял только улицу), поэтому гейт срабатывает только когда значение
# реально другое — иначе страница «Details» сломалась бы целиком.
from odoo import models
from odoo.exceptions import AccessError
from odoo.tools.translate import _

STUDENT_LOCKED_PARTNER_FIELDS = ('name', 'email', 'image_1920')


class Partner(models.Model):
    _inherit = 'res.partner'

    def _rost_is_locked_self_writer(self):
        """env сейчас — ученик, который пишет СВОЙ контакт."""
        user = self.env.user
        if not user or not user.id or user._is_public():
            return False
        return (
            self == user.partner_id
            and user.has_group('openeducat_core.group_op_students')
            and not user.has_group('rost_school_access.group_op_parent_rost')
            and not user.has_group('base.group_erp_manager')
        )

    def _rost_partner_value_changed(self, fname, value):
        """Меняется ли значение реально (для image — любая запись = попытка)."""
        if fname.startswith('image_'):
            return True
        old = self[fname]
        if isinstance(value, str) and isinstance(old, str):
            new, prev = value.strip(), old.strip()
            if fname == 'email':
                return new.casefold() != prev.casefold()
            return new != prev
        return value != old

    def write(self, vals):
        if self._rost_is_locked_self_writer():
            blocked = [
                fname for fname in STUDENT_LOCKED_PARTNER_FIELDS
                if fname in vals and self._rost_partner_value_changed(fname, vals[fname])
            ]
            if blocked:
                raise AccessError(_(
                    'Ученикам нельзя менять свои фото, имя и email — '
                    'обратитесь к администратору школы.'
                ))
        return super().write(vals)
