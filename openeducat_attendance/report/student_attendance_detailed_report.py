###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import time
import logging

from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class StudentAttendanceDetailedReport(models.AbstractModel):
    _name = "report.openeducat_attendance.student_attendance_detailed_report"
    _description = "Detailed Attendance Report"

    def get_student_name(self, data):
        student = self.env['op.student'].browse(data['student_id'])
        if student:
            return student.name
        return ""

    def get_detailed_data(self, data):
        """Get detailed attendance data including all sessions"""
        # Search for all attendance sheets in the date range
        sheet_search = self.env['op.attendance.sheet'].search(
            [('attendance_date', '>=', data['from_date']),
             ('attendance_date', '<=', data['to_date'])],
            order='attendance_date asc')

        lst = []
        for sheet in sheet_search:
            for line in sheet.attendance_line:
                # Include all attendance records for the student, not just absences
                if data['student_id'] == line.student_id.id:
                    # Determine status
                    if line.present:
                        status = "Present"
                    elif line.late:
                        status = "Late"
                    elif line.excused:
                        status = "Excused Absence"
                    elif line.absent:
                        status = "Unexcused Absence"
                    else:
                        status = "Unknown"

                    attendance_data = {
                        'date': sheet.attendance_date,
                        'course': sheet.register_id.course_id.name if sheet.register_id.course_id else '',
                        'status': status,
                        'remark': line.remark or '',
                        'mark': line.x_mark if hasattr(line, 'x_mark') else '',
                        'behavior': line.x_behavior if hasattr(line, 'x_behavior') else ''
                    }
                    lst.append(attendance_data)
        return lst

    def get_attendance_stats(self, data):
        """Calculate attendance statistics"""
        # Search for all attendance sheets in the date range
        sheet_search = self.env['op.attendance.sheet'].search(
            [('attendance_date', '>=', data['from_date']),
             ('attendance_date', '<=', data['to_date'])])

        total_sessions = 0
        present_count = 0
        absent_count = 0
        late_count = 0

        for sheet in sheet_search:
            for line in sheet.attendance_line:
                if data['student_id'] == line.student_id.id:
                    total_sessions += 1
                    if line.present:
                        present_count += 1
                    elif line.late:
                        late_count += 1
                        # Count late as present for attendance rate calculation
                        present_count += 1
                    elif line.excused or line.absent:
                        absent_count += 1

        # Calculate attendance rate
        if total_sessions > 0:
            attendance_rate = round((present_count / total_sessions) * 100, 2)
        else:
            attendance_rate = 0

        return {
            'total_sessions': total_sessions,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'attendance_rate': attendance_rate
        }

    def get_average_grades(self, data):
        """Calculate average grades for the student based on x_mark field in attendance"""
        _logger.info("DEBUG: get_average_grades called with data: %s", data)
        
        student_id = data['student_id']
        from_date = data['from_date']
        to_date = data['to_date']
        
        _logger.info("DEBUG: from_date: %s, to_date: %s", from_date, to_date)
        
        # Search for attendance records with x_mark for the student in the date range
        attendance_lines = self.env['op.attendance.line'].search([
            ('student_id', '=', student_id),
            ('attendance_id.attendance_date', '>=', from_date),
            ('attendance_id.attendance_date', '<=', to_date),
            ('x_mark', '!=', False)
        ])
        
        _logger.info("DEBUG: Found %d attendance lines with x_mark for student %s", len(attendance_lines), student_id)
        
        # Calculate average of x_mark values
        total_marks = 0
        grade_count = len(attendance_lines)
        average_grade = 0
        
        for line in attendance_lines:
            # Try to convert x_mark to number
            try:
                mark = float(line.x_mark)
                total_marks += mark
                _logger.info("DEBUG: Added mark %s from x_mark field", mark)
            except (ValueError, TypeError):
                # If x_mark is not a number, skip this record
                grade_count -= 1
                _logger.info("DEBUG: Skipped non-numeric x_mark value: %s", line.x_mark)
        
        _logger.info("DEBUG: total_marks: %s, grade_count: %s", total_marks, grade_count)
        
        if grade_count > 0:
            average_grade = round(total_marks / grade_count, 2)
        
        _logger.info("DEBUG: average_grade: %s, grade_count: %s", average_grade, grade_count)
        
        return {
            'average_grade': average_grade,
            'grade_count': grade_count
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        
        # Debug information
        print("DEBUG: _get_report_values called with data:", data)
        
        # Get statistics
        stats = self.get_attendance_stats(data) if data else {}
        grades = self.get_average_grades(data) if data else {}
        
        # Debug information
        print("DEBUG: stats:", stats)
        print("DEBUG: grades:", grades)
        
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'from_date': data['from_date'] if data else '',
            'to_date': data['to_date'] if data else '',
            'get_student_name': self.get_student_name(data) if data else "",
            'get_detailed_data': self.get_detailed_data(data) if data else [],
            'get_total_sessions': stats.get('total_sessions', 0),
            'get_present_count': stats.get('present_count', 0),
            'get_absent_count': stats.get('absent_count', 0),
            'get_late_count': stats.get('late_count', 0),
            'get_attendance_rate': stats.get('attendance_rate', 0),
            'get_average_grade': grades.get('average_grade', 0),
            'get_grade_count': grades.get('grade_count', 0)
        }
        
        # Debug information
        print("DEBUG: docargs:", docargs)
        
        return docargs