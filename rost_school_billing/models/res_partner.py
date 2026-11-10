# -*- coding: utf-8 -*-
"""Паспортные данные и адреса на контакте — источник токенов parent_*
для договоров. Видны только менеджеру приёмки и Администраторам."""
from odoo import fields, models

from .doc_engine import date_iso, fio_short

DOC_GROUPS = 'openeducat_admission.group_op_admission_user,base.group_system'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    rost_birth_date = fields.Date(
        'Дата рождения', groups=DOC_GROUPS)
    rost_passport_number = fields.Char(
        'Паспорт: серия и номер', groups=DOC_GROUPS,
        help="Как в договоре, одним полем: «40 20 781577».")
    rost_passport_issued_by = fields.Char(
        'Паспорт: кем выдан', groups=DOC_GROUPS)
    rost_passport_issue_date = fields.Date(
        'Паспорт: дата выдачи', groups=DOC_GROUPS)
    rost_passport_dept_code = fields.Char(
        'Паспорт: код подразделения', groups=DOC_GROUPS,
        help="«780-006».")
    rost_address_home = fields.Char(
        'Домашний адрес', groups=DOC_GROUPS,
        help="Адрес фактического проживания — для договора.")
    rost_address_reg = fields.Char(
        'Адрес регистрации', groups=DOC_GROUPS,
        help="Адрес регистрации по паспорту — для договора.")

    def _rost_partner_ctx(self):
        """Токены parent_* документа."""
        self.ensure_one()
        return {
            'parent_name': self.name or '',
            'parent_short': fio_short(self.name),
            'parent_birth_iso': date_iso(self.rost_birth_date),
            'parent_passport': self.rost_passport_number or '',
            'parent_passport_issued_by': self.rost_passport_issued_by or '',
            'parent_passport_issue_iso': date_iso(self.rost_passport_issue_date),
            'parent_passport_dept_code': self.rost_passport_dept_code or '',
            'parent_address_home': self.rost_address_home or '',
            'parent_address_reg': self.rost_address_reg or '',
            'parent_phone': self.mobile or self.phone or '',
            'parent_email': self.email or '',
        }
