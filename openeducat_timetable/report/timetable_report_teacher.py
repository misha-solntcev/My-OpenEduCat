import time

import pytz
from odoo import api, fields, models, tools

from .timetable_report_student import TimetableReportMixin


class ReportTimeTableTeacherGenerate(models.AbstractModel):
    _inherit = 'report.openeducat_timetable.timetable_mixin'
    _name = "report.openeducat_timetable.report_timetable_teacher_generate"
    _description = "Timetable Teacher Report"

    def _convert_to_local_timezone(self, time):
        '''
            Converts time as per local timezone.
        '''
        if time:
            timezone = pytz.timezone(self._context['tz'] or 'UTC')
            utc_in_time = pytz.UTC.localize(fields.Datetime.from_string(time))
            local_time = utc_in_time.astimezone(timezone)
            return local_time

    def get_full_name(self, data):
        faculty_name = self.env['op.faculty'].browse(data['faculty_id'][0])
        return faculty_name.name

    def sort_tt(self, data_list):
        main_list = []
        f = []
        for d in data_list:
            if d['period'] not in f:
                f.append(d['period'])
                main_list.append({
                    'name': d['period'],
                    'line': {d['day']: d},
                })
            else:
                for m in main_list:
                    if m['name'] == d['period']:
                        m['line'][d['day']] = d
        return main_list

    def get_object(self, data):
        data_list = []
        for timetable_obj in self.env['op.session'].browse(
                data['teacher_time_table_ids']):
            oldDate = pytz.UTC.localize(
                fields.Datetime.from_string(timetable_obj.start_datetime))
            day = str(oldDate.weekday())
            timetable_data = {
                'period': timetable_obj.timing,
                'start_datetime': self._convert_to_local_timezone(
                    timetable_obj.start_datetime).strftime(
                    tools.DEFAULT_SERVER_DATETIME_FORMAT),
                'day': day,
                'subject': timetable_obj.subject_id.name,
                'course': timetable_obj.course_id.name,
                'batch': timetable_obj.batch_id.name,
            }
            data_list.append(timetable_data)
        ttdl = sorted(data_list, key=lambda k: k['start_datetime'])
        return self.sort_tt(ttdl)

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        lines = self.get_object(data)
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'data': data,
            'time': time,
            'days': self.get_days(lines, data),
            'get_object': lambda d: lines,
            'get_full_name': self.get_full_name,
        }
        return docargs
