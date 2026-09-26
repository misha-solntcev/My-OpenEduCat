# -*- coding: utf-8 -*-
"""Оценки за домашнее задание в журнале урока (4 оценки: О1, О2, ДЗ 1, ДЗ 2).

ДЗ-оценки живут на строке сдачи задания урока
(sheet.homework_assignment_id -> op.assignment.sub.line, marks / marks_2).
Этот модуль — ЕДИНСТВЕННОЕ место, где доступно sheet.homework_assignment_id,
поэтому вся ДЗ-оценочная логика журнала живёт здесь (в openeducat_attendance
загрузка идёт раньше и related/depends на это поле падают с KeyError).

Миниапп читает те же данные: hw_sub_line_id / sub.marks / sub.marks_2 —
единый источник правды для журнала (ПК + миниапп) и блока ДЗ.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpAttendanceLineHw(models.Model):
    _inherit = 'op.attendance.line'

    # Задание ДЗ урока (для readonly-логики вьюхи).
    hw_assignment_id = fields.Many2one('op.assignment',
        related='attendance_id.homework_assignment_id', string='Задание ДЗ')

    # Строка сдачи этого ученика по заданию урока (может не существовать).
    hw_sub_line_id = fields.Many2one('op.assignment.sub.line',
        compute='_compute_hw_sub_line')

    hw_grade_1_ui = fields.Selection([('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        string='ДЗ 1', compute='_compute_hw_grade_ui', inverse='_set_hw_grade_1_ui')
    hw_grade_2_ui = fields.Selection([('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        string='ДЗ 2', compute='_compute_hw_grade_ui', inverse='_set_hw_grade_2_ui')

    # Средний балл: 4 оценки (О1, О2, ДЗ 1, ДЗ 2) поровну. Переопределяем
    # поле из openeducat_attendance — compute с ДЗ-зависимостями.
    grade_avg = fields.Float('Средний балл',
        compute='_rost_compute_grade_avg', store=True, aggregator="avg")

    @api.depends('attendance_id.homework_assignment_id.assignment_sub_line')
    def _compute_hw_sub_line(self):
        # sudo на чтение журнала: rule 611 режет ученику все op.attendance.sheet
        # (домен [(0,'=',1)]), а ДЗ-оценки мы обязаны отдавать ученику в
        # «Электронном дневнике» — columns hw_grade_1_ui/2_ui non-stored и
        # тянут этот compute на каждом чтении. Без sudo ученик получал
        # AccessError вместо дневника (см. логи prod, 20 uid, с 01.09).
        # Утечки нет: наружу уходит только marks/marks_2 своей строки сдачи.
        Sheet = self.env['op.attendance.sheet'].sudo()
        for rec in self:
            asg = Sheet.browse(rec.attendance_id.id).homework_assignment_id
            rec.hw_sub_line_id = (asg and asg.assignment_sub_line.filtered(
                lambda s: s.student_id == rec.student_id)[:1]) or False

    @api.depends('attendance_id.homework_assignment_id.assignment_sub_line.marks',
                 'attendance_id.homework_assignment_id.assignment_sub_line.marks_2')
    def _compute_hw_grade_ui(self):
        for rec in self:
            sub = rec.hw_sub_line_id
            rec.hw_grade_1_ui = str(int(sub.marks)) if sub and sub.marks > 0 else False
            rec.hw_grade_2_ui = str(int(sub.marks_2)) if sub and sub.marks_2 > 0 else False

    def _hw_set_grade(self, field_name, ui_value):
        """Запись ДЗ-оценки в строку сдачи; при отсутствии — создание.

        Приём без сдачи (устно/в тетради): создаём sub.line сразу
        с итоговым состоянием state='accept' — как /review_student
        в миниаппе. Задания на уроке нет — писать некуда.
        """
        self.ensure_one()
        asg = self.attendance_id.homework_assignment_id
        if not asg:
            raise ValidationError(_(
                "Оценка за ДЗ: у урока нет задания — сначала заполните домашнее задание."))
        val = float(ui_value) if ui_value else 0.0
        if val > 0 and not (2 <= val <= 5):
            raise ValidationError(_("Оценка должна быть от 2 до 5!"))
        sub = self.hw_sub_line_id
        if not sub:
            self.env['op.assignment.sub.line'].create({
                'assignment_id': asg.id,
                'student_id': self.student_id.id,
                'state': 'accept',
                field_name: val,
            })
        else:
            sub.write({field_name: val})

    def _set_hw_grade_1_ui(self):
        for rec in self:
            rec._hw_set_grade('marks', rec.hw_grade_1_ui)
    def _set_hw_grade_2_ui(self):
        for rec in self:
            rec._hw_set_grade('marks_2', rec.hw_grade_2_ui)

    @api.depends('grade_1', 'grade_2',
                 'attendance_id.homework_assignment_id.assignment_sub_line.marks',
                 'attendance_id.homework_assignment_id.assignment_sub_line.marks_2')
    def _rost_compute_grade_avg(self):
        for rec in self:
            sub = rec.hw_sub_line_id
            marks = [m for m in [
                rec.grade_1, rec.grade_2,
                sub.marks if sub else 0.0,
                sub.marks_2 if sub else 0.0,
            ] if m > 0]
            rec.grade_avg = sum(marks) / len(marks) if marks else 0.0

    @api.model
    def get_stats_from_lines(self, lines):
        """Супер: пересчёт оценок и среднего с учётом ДЗ-оценок."""
        res = super().get_stats_from_lines(lines)
        marks_all = []
        for l in lines:
            for v in [l.grade_1, l.grade_2]:
                if v and 2 <= v <= 5:
                    marks_all.append(v)
            sub = getattr(l, 'hw_sub_line_id', None)
            if sub:
                for v in [sub.marks, sub.marks_2]:
                    if v and 2 <= v <= 5:
                        marks_all.append(v)
        res['counts'] = {5: 0, 4: 0, 3: 0, 2: 0}
        for v in marks_all:
            res['counts'][int(v)] += 1
        res['avg'] = round(sum(marks_all) / len(marks_all), 2) if marks_all else 0.0
        return res

    def action_clear_grades(self):
        """Сброс всех 4 оценок строки (О1/О2 + ДЗ 1/ДЗ 2)."""
        super().action_clear_grades()
        for rec in self:
            if rec.hw_sub_line_id:
                rec.hw_sub_line_id.write({'marks': 0.0, 'marks_2': 0.0})


class OpAttendanceSheetHw(models.Model):
    _inherit = 'op.attendance.sheet'

    # Тумблеры ДЗ-колонок для массовых операций.
    mass_target_hw_1 = fields.Boolean('ДЗ 1')
    mass_target_hw_2 = fields.Boolean('ДЗ 2')

    # Статистика листа: та же математика + ДЗ-оценки.
    count_5 = fields.Integer(compute='_rost_compute_all_stats', store=True)
    count_4 = fields.Integer(compute='_rost_compute_all_stats', store=True)
    count_3 = fields.Integer(compute='_rost_compute_all_stats', store=True)
    count_2 = fields.Integer(compute='_rost_compute_all_stats', store=True)
    average_grade_lesson = fields.Float(compute='_rost_compute_all_stats', store=True)

    @api.depends('attendance_line', 'attendance_line.attendance_type_id',
                 'attendance_line.grade_1', 'attendance_line.grade_2',
                 'attendance_line.attendance_id.homework_assignment_id.assignment_sub_line.marks',
                 'attendance_line.attendance_id.homework_assignment_id.assignment_sub_line.marks_2')
    def _rost_compute_all_stats(self):
        for rec in self:
            counts = {5: 0, 4: 0, 3: 0, 2: 0}
            all_marks = []
            for line in rec.attendance_line:
                for val in [line.grade_1, line.grade_2]:
                    if val and 2 <= val <= 5:
                        counts[int(val)] += 1
                        all_marks.append(val)
                sub = line.hw_sub_line_id
                if sub:
                    for val in [sub.marks, sub.marks_2]:
                        if val and 2 <= val <= 5:
                            counts[int(val)] += 1
                            all_marks.append(val)
            rec.update({
                'count_5': counts[5],
                'count_4': counts[4],
                'count_3': counts[3],
                'count_2': counts[2],
                'average_grade_lesson': sum(all_marks) / len(all_marks) if all_marks else 0.0,
            })

    def action_mass_set_grade(self):
        """Супер: массовая оценка ДЗ-колонок (пишем через _ui-inverse)."""
        super().action_mass_set_grade()
        self.ensure_one()
        if self.state != 'start' or not self.attendance_line:
            return
        grade_val = self.env.context.get('set_grade')
        if not grade_val:
            return
        if not self.homework_assignment_id:
            return
        grade_float = float(grade_val)
        hw_toggles = {'hw_grade_1': self.mass_target_hw_1,
                      'hw_grade_2': self.mass_target_hw_2}
        for field_name, enabled in hw_toggles.items():
            if not enabled:
                continue
            empty_lines = self.attendance_line.filtered(
                lambda l: not l[field_name + '_ui'])
            if empty_lines:
                empty_lines.write({field_name + '_ui': str(int(grade_float))})

    def action_mass_clear_grades(self):
        """Супер: очистка ДЗ-оценок по тумблерам."""
        super().action_mass_clear_grades()
        hw_toggles = {'hw_grade_1': self.mass_target_hw_1,
                      'hw_grade_2': self.mass_target_hw_2}
        for field_name, enabled in hw_toggles.items():
            if not enabled:
                continue
            for line in self.attendance_line.filtered(
                    lambda l: l.hw_sub_line_id and l[field_name + '_ui']):
                line._hw_set_grade(
                    'marks' if field_name == 'hw_grade_1' else 'marks_2', False)


class OpAssignmentSubLineHw(models.Model):
    _inherit = 'op.assignment.sub.line'

    def write(self, vals):
        """При смене ДЗ-оценки пересчитываем средний балл журналов и
        статистику листа (grade_avg — store=True, путь через
        homework_assignment_id живёт в этом же модуле)."""
        res = super().write(vals)
        if 'marks' in vals or 'marks_2' in vals or 'state' in vals:
            Sub = self
            env = self.env
            lines = env['op.attendance.line'].search([
                ('attendance_id.homework_assignment_id', 'in', Sub.mapped('assignment_id').ids),
                ('student_id', 'in', Sub.mapped('student_id').ids),
            ])
            if lines:
                lines._rost_compute_grade_avg()
                lines.mapped('attendance_id')._rost_compute_all_stats()
        return res
