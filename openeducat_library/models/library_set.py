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
from odoo.exceptions import UserError, ValidationError


class LibrarySet(models.Model):
    _name = "library.set"
    _description = "Library Set (fixed kit per class)"
    _order = "name"

    name = fields.Char('Name', required=True)
    course_id = fields.Many2one(
        'op.course', 'Class', required=True,
        help='This set is assigned to this class.')
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        'library.set.line', 'set_id', 'Books in Set')

    _sql_constraints = [
        ('unique_course_set',
         'unique(course_id)',
         'Only one set per class is allowed!'),
    ]


class LibrarySetLine(models.Model):
    _name = "library.set.line"
    _description = "Library Set Line"
    _order = "sequence, id"

    set_id = fields.Many2one(
        'library.set', 'Set', required=True, ondelete='cascade')
    media_id = fields.Many2one(
        'op.media', 'Book', required=True)
    quantity = fields.Integer('Quantity', default=1, required=True)
    sequence = fields.Integer('Sequence', default=10)


class LibrarySetIssue(models.Model):
    _name = "library.set.issue"
    _description = "Library Set Issue"
    _order = "issued_date desc, id desc"
    _inherit = "mail.thread"

    name = fields.Char('Reference', compute='_compute_name', store=True)
    set_id = fields.Many2one(
        'library.set', 'Set', required=True,
        domain="[('active', '=', True)]")
    library_card_id = fields.Many2one(
        'op.library.card', 'Library Card', required=True)
    issued_date = fields.Date(
        'Issued Date', required=True, default=fields.Date.today())
    return_date = fields.Date('Return Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('returned', 'Returned'),
    ], 'State', default='draft', tracking=True)
    line_ids = fields.One2many(
        'library.set.issue.line', 'issue_id', 'Issue Lines')
    notes = fields.Text('Notes')

    @api.depends('set_id', 'library_card_id')
    def _compute_name(self):
        for rec in self:
            if rec.set_id and rec.library_card_id:
                rec.name = "%s / %s" % (
                    rec.set_id.name,
                    rec.library_card_id.partner_id.name or '')
            else:
                rec.name = ''

    @api.constrains('issued_date', 'return_date')
    def _check_date(self):
        for rec in self:
            if rec.issued_date and rec.return_date and \
                    rec.issued_date > rec.return_date:
                raise ValidationError(_(
                    'Return Date cannot be set before Issued Date.'))

    def _get_partner_id(self):
        self.ensure_one()
        card = self.library_card_id
        if card.type == 'student' and card.student_id:
            return card.student_id.partner_id.id
        elif card.type == 'faculty' and card.faculty_id:
            return card.faculty_id.partner_id.id
        return False

    def _check_max_issue(self, card, additional_count):
        """Check if card can take 'additional_count' more books."""
        current = self.env['op.media.movement'].search_count([
            ('library_card_id', '=', card.id),
            ('state', '=', 'issue'),
        ])
        allowed = card.library_card_type_id.allow_media
        return (current + additional_count) <= allowed

    def action_pick_units(self):
        """Auto-pick available media units for all lines."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Can only pick units in draft state.'))

        # Clear existing lines
        self.line_ids.unlink()

        IssueLine = self.env['library.set.issue.line']
        missing = []
        picked = []

        for set_line in self.set_id.line_ids:
            needed = set_line.quantity
            # Find available units for this media, matching the set's course
            domain = [
                ('media_id', '=', set_line.media_id.id),
                ('state', '=', 'available'),
            ]
            if self.set_id.course_id:
                domain.append(
                    ('course_ids', 'in', [self.set_id.course_id.id]))
            available_units = self.env['op.media.unit'].search(
                domain, limit=needed)

            if len(available_units) < needed:
                missing.append(
                    _("Not enough copies of '%s': need %d, found %d") % (
                        set_line.media_id.name, needed,
                        len(available_units)))

            for unit in available_units:
                IssueLine.create({
                    'issue_id': self.id,
                    'set_line_id': set_line.id,
                    'media_unit_id': unit.id,
                })
                picked.append(unit.name)

        msg_parts = []
        if picked:
            msg_parts.append(
                _("Picked %d unit(s): %s") % (
                    len(picked), ', '.join(picked)))
        if missing:
            msg_parts.append(
                _("Warnings:\n%s") % '\n'.join(missing))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_issue(self):
        """Issue all picked units, skipping those that exceed the limit."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Can only issue in draft state.'))
        if not self.line_ids:
            raise UserError(_(
                'No units picked. Please pick units first.'))

        card = self.library_card_id
        partner_id = self._get_partner_id()
        Movement = self.env['op.media.movement']

        # Get current count once
        current_count = Movement.search_count([
            ('library_card_id', '=', card.id),
            ('state', '=', 'issue'),
        ])
        allowed = card.library_card_type_id.allow_media

        errors = []
        success = 0
        skipped_limit = 0

        for line in self.line_ids:
            # Check per-unit limit before issuing
            if current_count >= allowed:
                skipped_limit += 1
                continue

            unit = line.media_unit_id
            if unit.state != 'available':
                errors.append(
                    _("SKIP: %s — already %s") % (
                        unit.name,
                        dict(unit._fields['state'].selection).get(unit.state)))
                continue

            Movement.create({
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
            line.state = 'issue'
            success += 1
            current_count += 1  # increment for next iteration check

        if success:
            self.state = 'issued'

        msg = _("Issued %d of %d unit(s).") % (
            success, len(self.line_ids))
        if skipped_limit:
            msg += _("\nSkipped %d (card limit: %d).") % (
                skipped_limit, card.library_card_type_id.allow_media)
        if errors:
            msg += "\n" + "\n".join(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Issue Result'),
                'message': msg,
                'type': 'success' if success else 'warning',
                'sticky': True,
            }
        }

    def action_return_all(self):
        """Return all issued lines in this set issue."""
        self.ensure_one()
        if self.state != 'issued':
            raise UserError(_('Can only return issued sets.'))

        lines_to_return = self.line_ids.filtered(
            lambda l: l.state == 'issue')
        if not lines_to_return:
            raise UserError(_('No issued lines to return.'))

        today = fields.Date.today()
        Movement = self.env['op.media.movement']
        success = 0
        errors = []

        for line in lines_to_return:
            unit = line.media_unit_id
            move = Movement.search([
                ('media_unit_id', '=', unit.id),
                ('state', '=', 'issue'),
            ], limit=1, order='id desc')
            if move:
                move.return_media(today)
                line.state = 'returned'
                success += 1
            else:
                errors.append(
                    _("No active movement found for %s") % unit.name)

        # If all lines returned, mark issue as returned
        remaining = self.line_ids.filtered(lambda l: l.state == 'issue')
        if not remaining:
            self.state = 'returned'

        msg = _("Returned %d of %d unit(s).") % (
            success, len(lines_to_return))
        if errors:
            msg += "\n" + "\n".join(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Return Result'),
                'message': msg,
                'type': 'success' if success else 'warning',
                'sticky': True,
            }
        }


class LibrarySetIssueLine(models.Model):
    _name = "library.set.issue.line"
    _description = "Library Set Issue Line"
    _order = "id"

    issue_id = fields.Many2one(
        'library.set.issue', 'Issue', required=True, ondelete='cascade')
    set_line_id = fields.Many2one(
        'library.set.line', 'Set Line', required=True)
    media_unit_id = fields.Many2one(
        'op.media.unit', 'Media Unit', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issue', 'Issued'),
        ('returned', 'Returned'),
    ], 'State', default='draft')

    def action_change_unit(self):
        """Open form view to change media unit."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change Media Unit'),
            'res_model': 'library.set.issue.line',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
