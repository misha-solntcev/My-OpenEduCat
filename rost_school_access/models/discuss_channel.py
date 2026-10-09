# -*- coding: utf-8 -*-
# Discuss: запрет ученикам создавать публичные каналы.
# ir.rule не работает (правила разных групп OR-ятся, у ученика есть базовое
# правило ядра с perm_create) — поэтому гейт в create().
from odoo import api, models
from odoo.exceptions import AccessError
from odoo.tools.translate import _


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            for vals in vals_list:
                # дефолт типа канала — 'channel' (публичный).
                # Создавать публичные каналы может только администрация:
                # рабочие каналы создаёт мастер каналов под админом.
                if vals.get('channel_type', 'channel') == 'channel':
                    groups = self.env.user.groups_id
                    admins = self.env.ref(
                        'openeducat_core.group_op_back_office_admin',
                        raise_if_not_found=False)
                    if not (admins and groups & admins):
                        raise AccessError(_(
                            'Создание каналов доступно только администрации.'
                        ))
        return super().create(vals_list)
