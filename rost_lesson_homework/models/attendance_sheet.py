from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class OpAttendanceSheet(models.Model):
    _inherit = 'op.attendance.sheet'

    lesson_homework = fields.Char('Домашнее задание', size=512)
    homework_assignment_id = fields.Many2one(
        'op.assignment', 'ДЗ (op.assignment)', readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Срок сдачи: следующий урок того же предмета у того же batch
    # ------------------------------------------------------------------
    def _next_lesson_datetime(self):
        self.ensure_one()
        now = fields.Datetime.now()
        nxt = self.env['op.session'].sudo().search([
            ('faculty_id', '=', self.session_id.faculty_id.id),
            ('subject_id', '=', self.subject_id.id),
            ('batch_id', '=', self.batch_id.id),
            ('start_datetime', '>', max(self.start_datetime, now)),
            ('state', '!=', 'cancel'),
        ], order='start_datetime asc', limit=1)
        return nxt.start_datetime if nxt else (
            now + timedelta(days=7))

    # ------------------------------------------------------------------
    # Авто-создание op.assignment при завершении урока
    # ------------------------------------------------------------------
    def _homework_sync(self):
        for sheet in self:
            if sheet.state not in ('done', 'start'):
                continue
            hw = (sheet.lesson_homework or '').strip()
            asg = sheet.homework_assignment_id

            if not hw:
                # ДЗ убрали из журнала — отменяем задание
                if asg and asg.state not in ('cancel', 'finish'):
                    asg.act_cancel()
                continue

            if asg:
                # Обновляем текст существующего задания
                vals = {}
                if asg.grading_assignment_id.name != hw:
                    asg.grading_assignment_id.name = hw
                if asg.description != hw:
                    vals['description'] = hw
                if vals:
                    asg.write(vals)
                if asg.state == 'cancel':
                    # Задание заново ввели после очистки — перепубликуем
                    asg.act_set_to_draft()
                    asg.act_publish()
                continue

            # Создаём новое задание
            atype = self.env['grading.assignment.type'].search([
                ('name', 'ilike', 'Домашнее задание')], limit=1)
            if not atype:
                raise UserError(
                    'Не найден тип задания «Домашнее задание». '
                    'Создайте его в модуле Задания.')
            sheet.homework_assignment_id = self.env['op.assignment'].create({
                'name': hw,
                'course_id': sheet.course_id.id,
                'subject_id': sheet.subject_id.id,
                'faculty_id': (sheet.faculty_id or sheet.session_id.faculty_id).id,
                'assignment_type': atype.id,
                'issued_date': fields.Datetime.now(),
                'submission_date': sheet._next_lesson_datetime(),
                'description': hw,
                'batch_id': sheet.batch_id.id,
                'state': 'publish',
                'allocation_ids': [
                    (6, 0, self.env['op.student'].search([
                        ('active_batch_id', '=', sheet.batch_id.id),
                        ('state', '=', 'studying'),
                    ]).ids)],
            })

    def write(self, vals):
        res = super().write(vals)
        if 'lesson_homework' in vals or 'state' in vals:
            self._homework_sync()
        return res

    def create(self, vals_list):
        sheets = super().create(vals_list)
        sheets._homework_sync()
        return sheets
