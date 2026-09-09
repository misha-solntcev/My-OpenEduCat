from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SessionReport(models.TransientModel):
    _name = "time.table.report"
    _description = "Generate Time Table Report"

    state = fields.Selection(
        [('faculty', 'Учитель'), ('student', 'Класс')],
        string='Тип отчёта', required=True, default='faculty')
    course_id = fields.Many2one('op.course', 'Параллель')
    batch_id = fields.Many2one('op.batch', 'Класс')
    faculty_id = fields.Many2one('op.faculty', 'Учитель')

    # Дефолты обязаны быть lambda: значение без lambda вычисляется ОДИН РАЗ
    # при загрузке модуля и застывает на дне недели старта сервера ( были
    # «воскресенье-воскресенье» + ложная ошибка «Select date range for a week»).
    start_date = fields.Date(
        'Дата начала', required=True,
        default=lambda self: fields.Date.context_today(self)
        - relativedelta(days=fields.Date.context_today(self).weekday()))
    end_date = fields.Date(
        'Дата окончания', required=True,
        default=lambda self: fields.Date.context_today(self)
        - relativedelta(days=fields.Date.context_today(self).weekday())
        + timedelta(days=6))

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for session in self:
            start_date = fields.Date.from_string(session.start_date)
            end_date = fields.Date.from_string(session.end_date)
            if end_date < start_date:
                raise ValidationError(_('End Date cannot be set before \
                Start Date.'))
            elif end_date > (start_date + timedelta(days=6)):
                raise ValidationError(_("Select date range for a week!"))

    @api.onchange('batch_id')
    def onchange_batch(self):
        # Параллель определяется классом автоматически (в каждой параллели
        # один класс) — в мастере её больше не выбирают.
        self.course_id = self.batch_id.course_id if self.batch_id else False

    def gen_time_table_report(self):
        template = self.env.ref(
            'openeducat_timetable.report_teacher_timetable_generate')
        data = self.read(
            ['start_date', 'end_date', 'course_id', 'batch_id', 'state',
             'faculty_id'])[0]
        if data['state'] == 'student':
            time_table_ids = self.env['op.session'].search(
                [('batch_id', '=', data['batch_id'][0]),
                 ('start_datetime', '>=', data['start_date']),
                 ('end_datetime', '<=', data['end_date'])],
                order='start_datetime asc')
            data.update({'time_table_ids': time_table_ids.ids})
            template = self.env.ref(
                'openeducat_timetable.report_student_timetable_generate')
        else:
            teacher_time_table_ids = self.env['op.session'].search(
                [('start_datetime', '>=', data['start_date']),
                 ('end_datetime', '<=', data['end_date']),
                 ('faculty_id', '=', data['faculty_id'][0])],
                order='start_datetime asc')
            data.update({'teacher_time_table_ids': teacher_time_table_ids.ids})
        return template.report_action(self, data=data)
