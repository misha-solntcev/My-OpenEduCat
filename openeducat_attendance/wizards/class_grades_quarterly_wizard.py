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

from odoo import models, fields, api


class ClassGradesQuarterly(models.TransientModel):
    _name = "class.grades.quarterly"
    _description = "Class Grades Quarterly"

    batch_id = fields.Many2one('op.batch', 'Batch', required=True)

    def print_report(self):
        data = {
            'batch_id': self.batch_id.id,
        }
        return self.env.ref('openeducat_attendance.action_report_class_grades_quarterly').report_action(self, data=data)