# -*- coding: utf-8 -*-
# «Требуется ответ» на ДЗ: флаг на журнале урока -> op.assignment,
# подхвачивается синком rost_lesson_homework и миниаппом (обязательное
# поле «Ответ» при сдаче).
from odoo import fields, models


class OpAttendanceSheet(models.Model):
    _inherit = 'op.attendance.sheet'

    homework_answer_required = fields.Boolean('Требуется ответ при сдаче')


class OpAssignment(models.Model):
    _inherit = 'op.assignment'

    answer_required = fields.Boolean('Требуется ответ при сдаче')


class OpAssignmentSubLine(models.Model):
    _inherit = 'op.assignment.sub.line'

    # Комментарий учителя при «на доработку»/приёмке. Отдельно от note:
    # note хранит ответ ученика (миниапп пишет его при сдаче).
    teacher_note = fields.Text('Комментарий учителя')
