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

from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class MassIssueMedia(models.TransientModel):
    _name = "mass.issue.media"
    _description = "Mass Issue Media Wizard"

    library_card_id = fields.Many2one(
        'op.library.card', 'Library Card', required=True)
    issued_date = fields.Date(
        'Issued Date', required=True, default=fields.Date.today())
    return_date = fields.Date('Return Date', required=True)
    unit_ids = fields.Many2many(
        'op.media.unit', string='Media Units',
        default=lambda self: self.env.context.get('active_ids', []))

    @api.constrains('issued_date', 'return_date')
    def _check_date(self):
        if self.issued_date > self.return_date:
            raise ValidationError(_(
                'Return Date cannot be set before Issued Date.'))

    @api.onchange('library_card_id')
    def onchange_library_card_id(self):
        if self.library_card_id:
            self.return_date = datetime.today() + relativedelta(
                days=self.library_card_id.library_card_type_id.duration)

    def _check_max_issue(self, library_card_id):
        media_movement_search = self.env["op.media.movement"].search(
            [('library_card_id', '=', library_card_id),
             ('state', '=', 'issue')])
        if len(media_movement_search) < self.env["op.library.card"].browse(
                library_card_id).library_card_type_id.allow_media:
            return True
        else:
            return False

    def do_mass_issue(self):
        self.ensure_one()
        if not self.unit_ids:
            raise UserError(_('No media units selected.'))

        if not self._check_max_issue(self.library_card_id.id):
            raise UserError(
                _('Maximum Number of media allowed for %s is : %s') %
                (self.library_card_id.partner_id.name,
                 self.library_card_id.library_card_type_id.allow_media))

        card = self.library_card_id
        partner_id = False
        if card.type == 'student' and card.student_id:
            partner_id = card.student_id.partner_id.id
        elif card.type == 'faculty' and card.faculty_id:
            partner_id = card.faculty_id.partner_id.id

        success = 0
        errors = []
        for unit in self.unit_ids:
            if unit.state != 'available':
                errors.append(
                    _("SKIP: %s — already %s") % (
                        unit.name,
                        dict(unit._fields['state'].selection).get(unit.state)))
                continue
            self.env['op.media.movement'].create({
                'media_id': unit.media_id.id,
                'media_unit_id': unit.id,
                'type': card.type,
                'student_id': card.student_id.id if card.type == 'student' else False,
                'faculty_id': card.faculty_id.id if card.type == 'faculty' else False,
                'library_card_id': card.id,
                'issued_date': self.issued_date,
                'return_date': self.return_date,
                'state': 'issue',
                'partner_id': partner_id,
            })
            unit.state = 'issue'
            success += 1

        msg = _("Issued %d media unit(s).") % success
        if errors:
            msg += "\n" + "\n".join(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mass Issue Result'),
                'message': msg,
                'type': 'success' if success else 'warning',
                'sticky': True,
            }
        }
