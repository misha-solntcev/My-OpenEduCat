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


class StudentGradesByDateReport(models.AbstractModel):
    _name = "report.openeducat_attendance.student_grades_by_date_report"
    _description = "Student Grades by Date Report"

    def get_subject_name(self, data):
        """Get subject name"""
        if data and data.get('subject_id'):
            subject = self.env['op.subject'].browse(data['subject_id'])
            if subject:
                return subject.name
        return ""

    def get_faculty_name(self, data):
        """Get faculty name"""
        if data and data.get('faculty_id'):
            faculty = self.env['op.faculty'].browse(data['faculty_id'])
            if faculty:
                return faculty.name
        return ""

    def get_batch_name(self, data):
        """Get batch name"""
        if data and data.get('batch_id'):
            batch = self.env['op.batch'].browse(data['batch_id'])
            if batch:
                return batch.name
        return ""

    def get_grades_by_date(self, data):
        """Get grades organized by student and lesson (attendance sheet)"""
        subject_id = data.get('subject_id')
        faculty_id = data.get('faculty_id')
        batch_id = data.get('batch_id')
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        
        # Check if required data is present
        if not all([subject_id, faculty_id, from_date, to_date]):
            return {'dates': [], 'students_data': []}
        
        # If batch_id is provided, get all students in that batch
        student_ids_in_batch = []
        if batch_id:
            students_in_batch = self.env['op.student'].search([('course_detail_ids.batch_id', '=', batch_id)])
            student_ids_in_batch = students_in_batch.ids
        
        # Build domain for attendance lines to find relevant sheets
        line_domain = [
            ('x_subject', '=', subject_id),
            ('x_faculty', '=', faculty_id),
            ('x_mark', '!=', False)
        ]
        
        # If batch filter is applied, add student filter
        if batch_id and student_ids_in_batch:
            line_domain.append(('student_id', 'in', student_ids_in_batch))
        elif batch_id and not student_ids_in_batch:
            # If batch is selected but no students found, return empty result
            return {'dates': [], 'students_data': []}
        
        # First, find all attendance lines matching our criteria
        matching_lines = self.env['op.attendance.line'].search(line_domain)
        
        # Then, get the attendance sheets from these lines, filtered by date
        attendance_sheets = self.env['op.attendance.sheet'].search([
            ('id', 'in', [line.attendance_id.id for line in matching_lines]),
            ('attendance_date', '>=', from_date),
            ('attendance_date', '<=', to_date)
        ], order='attendance_date asc, id asc')
        
        # Now refine our lines to only those in the matching sheets
        final_line_domain = [
            ('attendance_id', 'in', attendance_sheets.ids),
            ('x_subject', '=', subject_id),
            ('x_faculty', '=', faculty_id),
            ('x_mark', '!=', False)
        ]
        
        # If batch filter is applied, add student filter
        if batch_id and student_ids_in_batch:
            final_line_domain.append(('student_id', 'in', student_ids_in_batch))
        elif batch_id and not student_ids_in_batch:
            # If batch is selected but no students found, return empty result
            return {'dates': [], 'students_data': []}
        
        # Get all students who have marks for this subject and faculty in the date range
        student_lines = self.env['op.attendance.line'].search(final_line_domain)
        
        # Get unique students
        student_ids = list(set([line.student_id.id for line in student_lines]))
        students = self.env['op.student'].browse(student_ids)
        
        # Prepare data structure - use attendance sheet IDs instead of just dates
        # This allows us to distinguish between multiple lessons on the same date
        lesson_identifiers = [(sheet.id, sheet.attendance_date) for sheet in attendance_sheets]
        result = {
            'lesson_identifiers': lesson_identifiers,  # (sheet_id, date) tuples
            'students_data': []
        }
        
        # For each student, get their grades by lesson
        for student in students:
            student_data = {
                'student_name': student.name,
                'grades': {}
            }
        
            # Initialize all lessons with empty lists
            for sheet_id, date in lesson_identifiers:
                student_data['grades'][(sheet_id, date)] = []
            
            # Get attendance lines for this student, subject and faculty
            student_line_domain = [
                ('student_id', '=', student.id),
                ('attendance_id', 'in', attendance_sheets.ids),
                ('x_subject', '=', subject_id),
                ('x_faculty', '=', faculty_id),
                ('x_mark', '!=', False)
            ]
            
            student_lines = self.env['op.attendance.line'].search(student_line_domain)
            
            # Group grades by specific lesson (attendance sheet)
            for line in student_lines:
                sheet_id = line.attendance_id.id
                date = line.attendance_id.attendance_date
                # Only add grade to the specific lesson it belongs to
                if (sheet_id, date) in student_data['grades']:
                    try:
                        grade_value = int(line.x_mark)  # Convert to int as marks seem to be integers
                        student_data['grades'][(sheet_id, date)].append(grade_value)
                    except (ValueError, TypeError):
                        # Skip invalid grades
                        continue
            
            result['students_data'].append(student_data)
        
        # Sort students by name
        result['students_data'].sort(key=lambda x: x['student_name'])
        
        # Calculate and add average grades for each student
        all_student_averages = []
        all_grades = []
        for student_data in result['students_data']:
            student_grades = []
            # Collect all grades for this student
            for lesson_grades in student_data['grades'].values():
                student_grades.extend(lesson_grades)
            
            # Calculate student average
            if student_grades:
                student_average = round(sum(student_grades) / len(student_grades), 2)
                all_student_averages.append(student_average)
                all_grades.extend(student_grades)
            else:
                student_average = 0.0
            
            # Add average to student data
            student_data['average_grade'] = student_average
        
        # Calculate class average
        if all_grades:
            class_average = round(sum(all_grades) / len(all_grades), 2)
        else:
            class_average = 0.0
            
        result['class_average'] = class_average
        
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id')) if model else None
        
        grades_data = self.get_grades_by_date(data) if data else {}
        
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'from_date': data.get('from_date', '') if data else '',
            'to_date': data.get('to_date', '') if data else '',
            'get_subject_name': self.get_subject_name(data) if data else "",
            'get_faculty_name': self.get_faculty_name(data) if data else "",
            'get_batch_name': self.get_batch_name(data) if data else "",
            'get_grades_by_date': grades_data,
        }
        return docargs