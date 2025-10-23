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


class ClassGradesQuarterlyReport(models.AbstractModel):
    _name = "report.openeducat_attendance.class_grades_quarterly_report"
    _description = "Class Grades Quarterly Report"

    def get_batch_name(self, data):
        """Get class name"""
        batch = self.env['op.batch'].browse(data['batch_id'])
        if batch:
            return batch.name
        return ""

    def get_subjects_list(self, data):
        """Get list of all subjects for the class"""
        batch_id = data['batch_id']
        
        # Get all subject grades records for the specified batch
        subject_grades = self.env['op.subject.grades'].search([
            ('batch_id', '=', batch_id)
        ])
        
        # Collect unique subjects
        subjects = set()
        for record in subject_grades:
            if record.subject_id:
                subjects.add(record.subject_id.name)
        
        # Sort subjects alphabetically
        return sorted(list(subjects))


    def get_class_overall_average(self, data):
        """Calculate overall average grade for the entire class based on quarterly grades"""
        quarterly_data = self.get_quarterly_grades(data)
        
        # Collect all student averages
        all_student_averages = []
        for student_data in quarterly_data:
            student_grades = []
            for subject_grade in student_data['subjects'].values():
                if subject_grade and subject_grade.isdigit():
                    student_grades.append(float(subject_grade))
            
            if student_grades:
                student_average = round(sum(student_grades) / len(student_grades), 2)
                all_student_averages.append(student_average)
        
        # Calculate class average
        if all_student_averages:
            class_average = round(sum(all_student_averages) / len(all_student_averages), 2)
            return class_average
        else:
            return 0.0

    def get_quarterly_grades(self, data):
        """Get quarterly grades for all students in a class"""
        batch_id = data['batch_id']
        students = self.env['op.student'].search([
            ('course_detail_ids.batch_id', '=', batch_id)
        ])
        
        # Get all subject grades records for the specified batch
        subject_grades = self.env['op.subject.grades'].search([
            ('batch_id', '=', batch_id)
        ])
        
        # Collect unique subjects
        subjects = set()
        for record in subject_grades:
            if record.subject_id:
                subjects.add(record.subject_id.name)
        
        # Sort subjects alphabetically
        subjects = sorted(list(subjects))
        
        # Prepare data structure for results
        quarterly_data = []
        
        # For each student, get their quarterly grades by subject
        for student in students:
            student_data = {
                'student_name': student.name,
                'subjects': {}
            }
            
            # Initialize all subjects with empty values
            for subject in subjects:
                student_data['subjects'][subject] = ''
            
            # Search for subject grades records for the student
            subject_grades_records = self.env['op.subject.grades'].search([
                ('student_id', '=', student.id),
                ('batch_id', '=', batch_id)
            ])
            
            # Get quarterly grades by subject
            for record in subject_grades_records:
                if record.subject_id.name in student_data['subjects']:
                    student_data['subjects'][record.subject_id.name] = record.final_quarter_grade or ''
            
            quarterly_data.append(student_data)
        
        # Sort by student name
        quarterly_data.sort(key=lambda x: x['student_name'])
        
        return quarterly_data

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        
        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'get_batch_name': self.get_batch_name(data) if data else "",
            'get_subjects_list': self.get_subjects_list(data) if data else [],
            'get_quarterly_grades': self.get_quarterly_grades(data) if data else [],
            'get_class_overall_average': self.get_class_overall_average(data) if data else 0.0,
        }
        return docargs