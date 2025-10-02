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

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClassGradesSummary(models.TransientModel):
    _name = "class.grades.summary"
    _description = "Class Grades Summary"

    from_date = fields.Date(
        'From Date', required=True, default=lambda self: fields.Date.today())
    to_date = fields.Date(
        'To Date', required=True, default=lambda self: fields.Date.today())
    batch_id = fields.Many2one('op.batch', 'Class', required=True)

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for record in self:
            from_date = fields.Date.from_string(record.from_date)
            to_date = fields.Date.from_string(record.to_date)
            if to_date < from_date:
                raise ValidationError(
                    _("To Date cannot be set before From Date."))

    def print_report(self):
        data = self.read(['from_date', 'to_date', 'batch_id'])[0]
        # batch_id is a tuple (id, name) when read, we need just the id
        data['batch_id'] = data['batch_id'][0] if data['batch_id'] else None

        return self.env.ref(
            'openeducat_attendance.action_report_class_grades_summary') \
            .report_action(self, data=data)