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
from collections import defaultdict


class ClassGradesSummaryReport(models.AbstractModel):
    _name = "report.openeducat_attendance.class_grades_summary_report"
    _description = "Class Grades Summary Report"

    def get_batch_name(self, data):
        """Get class name"""
        batch = self.env['op.batch'].browse(data['batch_id'])
        if batch:
            return batch.name
        return ""

    def get_subjects_list(self, data):
        """Get list of all subjects with grades in the specified period"""
        batch_id = data['batch_id']
        from_date = data['from_date']
        to_date = data['to_date']
        
        # Get all attendance lines with marks for the class in the date range
        attendance_lines = self.env['op.attendance.line'].search([
            ('attendance_id.register_id.batch_id', '=', batch_id),
            ('attendance_id.attendance_date', '>=', from_date),
            ('attendance_id.attendance_date', '<=', to_date),
            ('x_mark', '!=', False),
            ('x_subject', '!=', False)
        ])
        
        # Collect unique subjects
        subjects = set()
        for line in attendance_lines:
            if line.x_subject:
                try:
                    # Get subject name from the subject record
                    subject = self.env['op.subject'].browse(int(line.x_subject))
                    if subject:
                        subjects.add(subject.name)
                except (ValueError, TypeError):
                    # Skip invalid subject references
                    continue
        
        # Sort subjects alphabetically
        return sorted(list(subjects))

    def get_class_grades_summary_by_subject(self, data):
        """Get grades summary for all students in a class, organized by subjects"""
        batch_id = data['batch_id']
        from_date = data['from_date']
        to_date = data['to_date']
        
        # Get all students in the class
        students = self.env['op.student'].search([
            ('course_detail_ids.batch_id', '=', batch_id)
        ])
        
        # Get list of subjects
        subjects = self.get_subjects_list(data)
        
        # Prepare data structure for results
        class_data = []
        
        # For each student, get their grades by subject
        for student in students:
            student_data = {
                'student_name': student.name,
                'subjects': {}
            }
            
            # Initialize all subjects with empty lists
            for subject in subjects:
                student_data['subjects'][subject] = []
            
            # Search for attendance records with x_mark for the student in the date range
            attendance_lines = self.env['op.attendance.line'].search([
                ('student_id', '=', student.id),
                ('attendance_id.attendance_date', '>=', from_date),
                ('attendance_id.attendance_date', '<=', to_date),
                ('x_mark', '!=', False),
                ('x_subject', '!=', False)
            ])
            
            # Group grades by subject
            for line in attendance_lines:
                try:
                    grade_value = float(line.x_mark)
                    # Get subject name
                    if line.x_subject:
                        subject = self.env['op.subject'].browse(int(line.x_subject))
                        if subject and subject.name in student_data['subjects']:
                            student_data['subjects'][subject.name].append(grade_value)
                except (ValueError, TypeError):
                    # Skip non-numeric grades or invalid subject references
                    continue
            
            # Calculate average grade for this student
            all_grades = []
            for subject_grades in student_data['subjects'].values():
                all_grades.extend(subject_grades)
            
            average_grade = 0.0
            if all_grades:
                average_grade = round(sum(all_grades) / len(all_grades), 2)
            
            student_data['average_grade'] = average_grade
            class_data.append(student_data)
        
        # Sort by student name
        class_data.sort(key=lambda x: x['student_name'])
        
        return class_data

    def get_class_overall_average(self, data):
        """Calculate overall average grade for the entire class"""
        class_grades_data = self.get_class_grades_summary_by_subject(data)
        
        # Collect all student averages
        all_student_averages = [student_data['average_grade'] 
                               for student_data in class_grades_data 
                               if student_data['average_grade'] > 0]
        
        # Calculate class average
        if all_student_averages:
            class_average = round(sum(all_student_averages) / len(all_student_averages), 2)
            return class_average
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
            'get_batch_name': self.get_batch_name(data) if data else "",
            'get_subjects_list': self.get_subjects_list(data) if data else [],
            'get_class_grades_summary': self.get_class_grades_summary_by_subject(data) if data else [],
            'get_class_overall_average': self.get_class_overall_average(data) if data else 0.0,
        }
        return docargs