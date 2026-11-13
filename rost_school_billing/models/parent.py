# -*- coding: utf-8 -*-
"""Личные данные родителя — в SIS (op.parent), не в контактах.

Решение 12.11.2026: персональные данные собираются во вкладках приёмки
и живут в SIS (меню «Родители»); контакты res.partner остаются по
стандарту Odoo — имя, телефон, email. Источник токенов parent_* для
договоров — эти поля (переехали с res.partner, миграция rost_* -> op.parent).
"""
from odoo import fields, models


class OpParent(models.Model):
    _inherit = 'op.parent'

    birth_date = fields.Date('Дата рождения')
    passport_number = fields.Char(
        'Паспорт: серия и номер',
        help="Как в договоре, одним полем: «40 20 781577».")
    passport_issued_by = fields.Char('Паспорт: кем выдан')
    passport_issue_date = fields.Date('Паспорт: дата выдачи')
    passport_dept_code = fields.Char(
        'Паспорт: код подразделения',
        help="«780-006».")
    address_reg = fields.Char(
        'Адрес регистрации',
        help="Адрес регистрации по паспорту — для договора.")
    address_home = fields.Char(
        'Адрес фактического проживания',
        help="Домашний адрес — для договора.")

    # Канбан (12.11.2026): аватар из стандартного контакта, счётчик детей.
    # related несторовый: partner.image_1920 сам несторовый (compute поверх
    # ir.attachment), store здесь молча не хранится — читается напрямую.
    image_1920 = fields.Image(related='name.image_1920')
    avatar_128 = fields.Image(related='name.avatar_128')
    student_count = fields.Integer(
        'Детей', compute='_compute_student_count')

    def _compute_student_count(self):
        for parent in self:
            parent.student_count = len(parent.student_ids)
