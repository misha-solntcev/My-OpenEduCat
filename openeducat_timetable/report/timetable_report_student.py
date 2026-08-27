import time
from datetime import timedelta

import pytz
from odoo import api, fields, models, tools

DAY_NAMES = {
    '0': 'Понедельник',
    '1': 'Вторник',
    '2': 'Среда',
    '3': 'Четверг',
    '4': 'Пятница',
    '5': 'Суббота',
    '6': 'Воскресенье',
}


class TimetableReportMixin(models.AbstractModel):
    """Общая логика печати расписания: колонки дней по выбранному периоду.

    Правила колонок:
    - Пн-Пт печатаются всегда, если попадают в выбранный диапазон дат;
    - Суббота печатается только если на неё есть уроки;
    - Воскресенье не печатается.
    """

    _name = 'report.openeducat_timetable.timetable_mixin'
    _description = 'Timetable Report Mixin'

    def _convert_to_local_timezone(self, time):
        '''
            Converts time as per local timezone.
        '''
        if time:
            timezone = pytz.timezone(self._context['tz'] or 'UTC')
            utc_in_time = pytz.UTC.localize(fields.Datetime.from_string(time))
            local_time = utc_in_time.astimezone(timezone)
            return local_time

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

    def get_days(self, lines, data):
        """Колонки дней для шапки: [(day_key, название)] по выбранному периоду."""
        # Extract day keys from the inner 'line' dictionary structure
        seen = {day_key for l in lines for day_key in l.get('line', {})}
        
        days = []
        curr = fields.Date.from_string(data['start_date'])
        end = fields.Date.from_string(data['end_date'])
        while curr <= end:
            key = str(curr.weekday())
            # Пн-Пт всегда; Сб — только с уроками; Вс — никогда.
            if key in ('0', '1', '2', '3', '4') or (key == '5' and key in seen):
                days.append((key, DAY_NAMES[key]))
            curr += timedelta(days=1)
        return days


class ReportTimetableStudentGenerate(models.AbstractModel):
    _inherit = 'report.openeducat_timetable.timetable_mixin'
    _name = "report.openeducat_timetable.report_timetable_student_generate"
    _description = "Timetable Student Report"

    def get_object(self, data):
        data_list = []
        for timetable_obj in self.env['op.session'].browse(
                data['time_table_ids']):
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
        }
        return docargs
