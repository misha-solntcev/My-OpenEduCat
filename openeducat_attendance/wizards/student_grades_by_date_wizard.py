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

import logging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import date

_logger = logging.getLogger(__name__)


class StudentGradesByDate(models.TransientModel):
    _name = "student.grades.by.date"
    _description = "Student Grades by Date"

    from_date = fields.Date(
        'From Date', required=True, default=lambda self: self._get_default_from_date())
    to_date = fields.Date(
        'To Date', required=True, default=lambda self: fields.Date.today())
    subject_id = fields.Many2one('op.subject', 'Subject', required=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty', required=True)
    batch_id = fields.Many2one('op.batch', 'Batch')

    @api.model
    def _get_default_from_date(self):
        """Get default from date as the start of the current academic year"""
        # Try to find the current academic year based on today's date
        today = date.today()
        
        # Search for academic years that include today's date
        current_year = self.env['op.academic.year'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today)
        ], limit=1)
        
        # If we found a current academic year, use its start date
        if current_year:
            return current_year.start_date
            
        # Fallback to September 1st of current or previous year
        if today.month < 9:
            return date(today.year - 1, 9, 1)
        else:
            return date(today.year, 9, 1)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            from_date = fields.Date.from_string(record.from_date)
            to_date = fields.Date.from_string(record.to_date)
            if to_date < from_date:
                raise ValidationError(
                    _("To Date cannot be set before From Date."))

    def print_report(self):
        # Fallback to original method if performance utils fail
        data = self.read(['from_date', 'to_date', 'subject_id', 'faculty_id', 'batch_id'])[0]
        data['subject_id'] = data['subject_id'][0] if data['subject_id'] else None
        data['faculty_id'] = data['faculty_id'][0] if data['faculty_id'] else None
        data['batch_id'] = data['batch_id'][0] if data['batch_id'] else None

        return self.env.ref(
            'openeducat_attendance.action_report_student_grades_by_date') \
            .report_action(self, data=data)