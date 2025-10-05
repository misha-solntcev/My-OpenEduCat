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
from odoo import api, models


class StudentGradesBySubjectReport(models.AbstractModel):
    _name = "report.openeducat_attendance.student_grades_by_subject_report"
    _description = "Student Grades by Subject Report"

    def get_student_name(self, data):
        """Get student name"""
        student = self.env['op.student'].browse(data['student_id'])
        if student:
            return student.name
        return ""

    def get_grades_by_subject(self, data):
        """Get grades grouped by subject"""
        student_id = data['student_id']
        from_date = data['from_date']
        to_date = data['to_date']
        
        # Search for attendance records with x_mark for the student in the date range
        attendance_lines = self.env['op.attendance.line'].search([
            ('student_id', '=', student_id),
            ('attendance_id.attendance_date', '>=', from_date),
            ('attendance_id.attendance_date', '<=', to_date),
            ('x_mark', '!=', False)
        ])
        
        # Group grades by subject
        subjects_data = {}
        
        for line in attendance_lines:
            # Get subject from attendance line (x_subject field)
            if line.x_subject:
                subject = self.env['op.subject'].browse(int(line.x_subject))
                if subject:
                    subject_name = subject.name
                    mark = line.x_mark
                    behavior = line.x_behavior if hasattr(line, 'x_behavior') else ''
                    date = line.attendance_id.attendance_date
                    
                    # Initialize subject data if not exists
                    if subject_name not in subjects_data:
                        subjects_data[subject_name] = {
                            'subject_name': subject_name,
                            'grades': [],
                            'average': 0.0
                        }
                    
                    # Add grade details to subject
                    try:
                        grade_value = float(mark)
                        grade_details = {
                            'date': date,
                            'mark': grade_value,
                            'behavior': behavior,
                            'remark': line.remark or ''
                        }
                        subjects_data[subject_name]['grades'].append(grade_details)
                    except (ValueError, TypeError):
                        # Skip non-numeric grades
                        continue
        
        # Calculate average for each subject
        for subject_name, subject_data in subjects_data.items():
            grades = [g['mark'] for g in subject_data['grades']]
            if grades:
                subject_data['average'] = round(sum(grades) / len(grades), 2)
            else:
                subject_data['average'] = 0.0
        
        # Convert to list and sort by subject name
        result = list(subjects_data.values())
        result.sort(key=lambda x: x['subject_name'])
        
        return result

    def get_overall_average(self, data):
        """Calculate overall average grade across all subjects"""
        grades_by_subject = self.get_grades_by_subject(data)
        
        # Collect all grades from all subjects
        all_grades = []
        for subject_data in grades_by_subject:
            all_grades.extend([g['mark'] for g in subject_data['grades']])
        
        # Calculate overall average
        if all_grades:
            overall_average = round(sum(all_grades) / len(all_grades), 2)
            return overall_average
        else:
            return 0.0

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'from_date': data['from_date'] if data else '',
            'to_date': data['to_date'] if data else '',
            'get_student_name': self.get_student_name(data) if data else "",
            'get_grades_by_subject': self.get_grades_by_subject(data) if data else [],
            'get_overall_average': self.get_overall_average(data) if data else 0.0,
        }
        return docargs