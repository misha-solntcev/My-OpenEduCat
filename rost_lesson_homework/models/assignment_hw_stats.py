# -*- coding: utf-8 -*-
"""Счётчики и состояние ДЗ на задании — ЕДИНСТВЕННЫЙ источник формулы.

Вынесено из rost_max_miniapp/controllers/timetable.py (2026-10-15, решение
Миши): формула сегментации «К проверке / Выдано / Проверено» раньше жила в
контроллере в ДВУХ местах (лента my_homework + сводка hw_summary) — теперь
она здесь, а контроллер и ПК-список читают одни и те же поля.

store=True обязателен: по «Состоянию ДЗ» нужны фильтры и группировка
Odoo (список из смарт-кнопки журнала), а группировка по non-stored
compute невозможна.
"""
from odoo import api, fields, models


class OpAssignmentHwStats(models.Model):
    _inherit = 'op.assignment'

    # M в «сдали N из M» — назначенные ученики (заполняет журнал урока).
    x_hw_total = fields.Integer(
        'Учеников', compute='_compute_hw_stats', store=True)
    # «Сдали N» — строки сдач в любом рабочем состоянии (submit + accept).
    x_hw_submitted = fields.Integer(
        'Сдали', compute='_compute_hw_stats', store=True)
    # Непроверенные сдачи (submit) — то, что зовёт учителя к работе.
    x_hw_to_review = fields.Integer(
        'На проверке', compute='_compute_hw_stats', store=True)
    # Принято (accept).
    x_hw_accepted = fields.Integer(
        'Принято', compute='_compute_hw_stats', store=True)
    # Есть несдавшие — для фильтра «Просрочено» (сравнение поле-поле в
    # domain не поддерживается, поэтому храним готовый булев флаг).
    x_hw_missing = fields.Boolean(
        'Есть несдавшие', compute='_compute_hw_stats', store=True)

    # Состояние ДЗ — формула сегментации миниаппа (hw_summary), слово в слово:
    #   review  = publish и есть непроверенные сдачи;
    #   issued  = publish и сдач нет;
    #   checked = finish ИЛИ (publish и сдачи есть и все приняты);
    #   draft/cancel — pass-through, чтобы список не врал о неопубликованных.
    x_hw_state = fields.Selection([
        ('draft', 'Черновик'),
        ('issued', 'Выдано'),
        ('review', 'На проверке'),
        ('checked', 'Проверено'),
        ('cancel', 'Отменено'),
    ], string='Состояние ДЗ', compute='_compute_hw_state', store=True)

    @api.depends('allocation_ids', 'assignment_sub_line.state')
    def _compute_hw_stats(self):
        for a in self:
            lines = a.assignment_sub_line
            a.x_hw_total = len(a.allocation_ids)
            a.x_hw_submitted = len(
                lines.filtered(lambda l: l.state in ('submit', 'accept')))
            a.x_hw_to_review = len(
                lines.filtered(lambda l: l.state == 'submit'))
            a.x_hw_accepted = len(lines.filtered(lambda l: l.state == 'accept'))
            a.x_hw_missing = a.x_hw_submitted < a.x_hw_total

    @api.depends('state', 'assignment_sub_line.state')
    def _compute_hw_state(self):
        for a in self:
            if a.state == 'draft':
                a.x_hw_state = 'draft'
            elif a.state == 'cancel':
                a.x_hw_state = 'cancel'
            elif a.state == 'finish':
                a.x_hw_state = 'checked'
            else:
                if a.x_hw_to_review > 0:
                    a.x_hw_state = 'review'
                elif a.x_hw_submitted == 0:
                    a.x_hw_state = 'issued'
                else:
                    a.x_hw_state = 'checked'

    # ------------------------------------------------------------------
    # Доступ из журнала: смарт-кнопка «На проверке N» + окно списка
    # ------------------------------------------------------------------
    def _hw_teacher_assignments_domain(self, subject, faculty):
        """Скоуп «задания этого учителя по этому предмету».

        Кнопка = обещание: счётчик в бейдже и строки открывшегося окна
        считаются по одному предикату, поэтому фильтр «На проверке»
        передаётся в context (снимаемый тег), а не в domain.
        """
        domain = []
        if faculty:
            domain.append(('faculty_id', '=', faculty.id))
        if subject:
            domain.append(('subject_id', '=', subject.id))
        return domain

    def _hw_review_count(self, subject, faculty):
        """Число заданий учителя по предмету с непроверенными сдачами."""
        if not subject or not faculty:
            return 0
        return self.sudo().search_count(
            self._hw_teacher_assignments_domain(subject, faculty)
            + [('state', '=', 'publish'), ('x_hw_state', '=', 'review')])
