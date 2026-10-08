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
        if not self.env.su and not self._skip_student_gate():
            for vals in vals_list:
                # дефолт типа канала — 'channel' (публичный)
                if vals.get('channel_type', 'channel') == 'channel':
                    raise AccessError(_(
                        'Создание каналов доступно только учителям и администрации.'
                    ))
        return super().create(vals_list)

    def _skip_student_gate(self):
        user = self.env.user
        groups = user.groups_id
        if groups & self.env.ref('openeducat_core.group_op_faculty', raise_if_not_found=False):
            return True
        if groups & self.env.ref(
                'openeducat_core.group_op_back_office_admin', raise_if_not_found=False):
            return True
        return False
