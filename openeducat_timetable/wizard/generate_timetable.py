import calendar
import datetime
import time

import pytz
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class GenerateSession(models.TransientModel):
    _name = "generate.time.table"
    _description = "Generate Sessions"
    _rec_name = "course_id"

    course_id = fields.Many2one('op.course', 'Course', required=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    time_table_lines = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines')
    time_table_lines_1 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines1',
        domain=[('day', '=', '0')])
    time_table_lines_2 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines2',
        domain=[('day', '=', '1')])
    time_table_lines_3 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines3',
        domain=[('day', '=', '2')])
    time_table_lines_4 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines4',
        domain=[('day', '=', '3')])
    time_table_lines_5 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines5',
        domain=[('day', '=', '4')])
    time_table_lines_6 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines6',
        domain=[('day', '=', '5')])
    time_table_lines_7 = fields.One2many(
        'gen.time.table.line', 'gen_time_table', 'Time Table Lines7',
        domain=[('day', '=', '6')])
    start_date = fields.Date(
        'Start Date', required=True, default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date', required=True)

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        start_date = fields.Date.from_string(self.start_date)
        end_date = fields.Date.from_string(self.end_date)
        if start_date > end_date:
            raise ValidationError(_("End Date cannot be set before \
            Start Date."))

    @api.onchange('course_id')
    def onchange_course(self):
        if self.batch_id and self.course_id:
            if self.batch_id.course_id != self.course_id:
                self.batch_id = False

    def change_tz(self, date):
        local_tz = pytz.timezone(
            self.env.user.partner_id.tz or 'GMT')
        local_dt = local_tz.localize(date, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        return datetime.datetime.strptime(
            utc_dt, "%Y-%m-%d %H:%M:%S")

    def act_gen_time_table(self):
        session_obj = self.env['op.session']
        data = []
        for session in self:
            start_date = session.start_date
            end_date = session.end_date
            for n in range((end_date - start_date).days + 1):
                curr_date = start_date + datetime.timedelta(n)
                for line in session.time_table_lines:
                    if int(line.day) == curr_date.weekday():
                        if line.timing_id:
                            h, m = line.timing_id.lesson_hour, line.timing_id.lesson_minute
                            duration = line.timing_id.duration
                            final_start_date = datetime.datetime.combine(curr_date, datetime.time(h, m))
                            final_end_date = final_start_date + datetime.timedelta(minutes=duration)
                        else:
                            # Резервный вариант, если урок не выбран
                            final_start_date = datetime.datetime.combine(
                                curr_date, datetime.time(int(line.session_start_time), 
                                int((line.session_start_time % 1) * 60)))
                            final_end_date = final_start_date + datetime.timedelta(minutes=40)
                        
                        curr_start_date = self.change_tz(final_start_date)
                        curr_end_date = self.change_tz(final_end_date)
                        data.append({
                            'faculty_id': line.faculty_id.id,
                            'subject_id': line.subject_id.id,
                            'course_id': session.course_id.id,
                            'batch_id': session.batch_id.id,
                            'timing_id': line.timing_id.id,
                            'classroom_id': line.classroom_id.id,
                            'start_datetime': curr_start_date.strftime("%Y-%m-%d %H:%M:%S"),
                            'end_datetime': curr_end_date.strftime("%Y-%m-%d %H:%M:%S"),
                        })
            if data:
                session_obj.create(data)
            return {'type': 'ir.actions.act_window_close'}


class GenerateSessionLine(models.TransientModel):
    _name = 'gen.time.table.line'
    _description = 'Generate Time Table Lines'
    _rec_name = 'day'

    gen_time_table = fields.Many2one(
        'generate.time.table', 'Time Table', required=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', required=True)
    subject_id = fields.Many2one('op.subject', 'Subject', required=True)
    timing_id = fields.Many2one('op.timing', 'Lesson Slot', required=True)
    session_start_time = fields.Float("Start Time")
    session_end_time = fields.Float("End Time")
    classroom_id = fields.Many2one('op.classroom', 'Classroom')
    day = fields.Selection([
        ('0', calendar.day_name[0]),
        ('1', calendar.day_name[1]),
        ('2', calendar.day_name[2]),
        ('3', calendar.day_name[3]),
        ('4', calendar.day_name[4]),
        ('5', calendar.day_name[5]),
        ('6', calendar.day_name[6]),
    ], 'Day', required=True)
