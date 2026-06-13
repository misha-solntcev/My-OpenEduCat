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
    media_ids = fields.Many2many('op.media', string='Books')

    _sql_constraints = [
        ('unique_course_set',
         'unique(course_id)',
         'Only one set per class is allowed!'),
    ]


class LibrarySetIssue(models.Model):
    _name = "library.set.issue"
    _description = "Library Set Issue"
    _order = "issued_date desc, id desc"
    _inherit = "mail.thread"

    name = fields.Char('Reference', compute='_compute_name', store=True)
    set_id = fields.Many2one(
        'library.set', 'Set', required=True, domain="[('active', '=', True)]")
    library_card_id = fields.Many2one('op.library.card', 'Library Card', required=True)
    issued_date = fields.Date('Issued Date', required=True, default=fields.Date.today())
    return_date = fields.Date('Return Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('partial_return', 'Partial Return'),
        ('returned', 'Returned'),
    ], 'State', default='draft', tracking=True)

    unit_ids = fields.Many2many('op.media.unit', string='Media Units')
    notes = fields.Text('Notes')

    # Computed for available units (preview, not editable)
    available_unit_ids = fields.Many2many(
        'op.media.unit', string='Available Units',
        compute='_compute_available_units')

    @api.depends('set_id')
    def _compute_available_units(self):
        """Show available units from set's media for preview (draft state)."""
        for rec in self:
            if rec.state == 'draft' and rec.set_id:
                units = self.env['op.media.unit'].search([
                    ('media_id', 'in', rec.set_id.media_ids.ids),
                    ('state', '=', 'available'),
                ])
                rec.available_unit_ids = units
            else:
                rec.available_unit_ids = False

    @api.depends('set_id', 'library_card_id')
    def _compute_name(self):
        for rec in self:
            if rec.set_id and rec.library_card_id:
                partner_name = rec.library_card_id.partner_id.name or ''
                rec.name = f"{rec.set_id.name} / {partner_name}"
            else:
                rec.name = ''

    @api.constrains('issued_date', 'return_date')
    def _check_date(self):
        for rec in self:
            if rec.issued_date and rec.return_date and \
                    rec.issued_date > rec.return_date:
                raise ValidationError(_(
                    'Return Date cannot be set before Issued Date.'))

    def action_pick_units(self):
        """Auto-pick available media units for all books in the set.
        Adds units to unit_ids (doesn't replace) for flexibility."""
        self.ensure_one()
        if self.state not in ('draft', 'returned'):
            raise UserError(_('Can only pick units in draft state.'))

        units_to_add = []
        missing = []
        picked = []

        for media in self.set_id.media_ids:
            domain = [
                ('media_id', '=', media.id),
                ('state', '=', 'available'),
            ]
            if self.set_id.course_id:
                domain.append(
                    ('course_ids', 'in', [self.set_id.course_id.id]))
            unit = self.env['op.media.unit'].search(domain, limit=1)
            if unit and unit.id not in self.unit_ids.ids:
                picked.append(unit.name)
                units_to_add.append(unit.id)
            elif not unit:
                missing.append(_("No available copy of '%s'") % media.name)

        if units_to_add:
            self.unit_ids = [(4, uid) for uid in units_to_add]

        msg_parts = []
        if picked:
            msg_parts.append(
                _("Added %d unit(s) to selection: %s") % (
                    len(picked), ', '.join(picked)))
        if missing:
            msg_parts.append(
                _("Missing:\n%s") % '\n'.join(missing))

        if msg_parts:
            self.message_post(body='\n'.join(msg_parts))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_issue(self):
        """Issue all picked units."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Can only issue in draft state.'))
        if not self.unit_ids:
            raise UserError(_(
                'No units picked. Please pick units first.'))

        card = self.library_card_id
        Movement = self.env['op.media.movement']

        # Current count on card
        current_count = Movement.search_count([
            ('library_card_id', '=', card.id),
            ('state', '=', 'issue'),
        ])
        allowed = card.library_card_type_id.allow_media

        errors = []
        success = 0
        skipped_limit = 0
        movements_vals = []
        units_to_issue = []

        for unit in self.unit_ids:
            if current_count >= allowed:
                skipped_limit += 1
                continue

            if unit.state != 'available':
                state_label = dict(
                    self.env['op.media.unit']._fields['state'].selection
                ).get(unit.state)
                errors.append(_(f"SKIP: {unit.name} — already {state_label}"))
                continue

            # Get partner inline (was _get_partner_id)
            if card.type == 'student' and card.student_id:
                partner_id = card.student_id.partner_id.id
                student_id = card.student_id.id
                faculty_id = False
            elif card.type == 'faculty' and card.faculty_id:
                partner_id = card.faculty_id.partner_id.id
                student_id = False
                faculty_id = card.faculty_id.id
            else:
                partner_id = False
                student_id = False
                faculty_id = False

            movements_vals.append({
                'media_id': unit.media_id.id,
                'media_unit_id': unit.id,
                'type': card.type,
                'student_id': student_id,
                'faculty_id': faculty_id,
                'library_card_id': card.id,
                'issued_date': self.issued_date,
                'return_date': self.return_date,
                'state': 'issue',
                'partner_id': partner_id,
            })
            units_to_issue.append(unit)
            success += 1
            current_count += 1

        if movements_vals:
            Movement.create(movements_vals)
            # Bulk update unit states
            if units_to_issue:
                self.env['op.media.unit'].browse(
                    [u.id for u in units_to_issue]
                ).write({'state': 'issue'})

        if success:
            self.state = 'issued'

        msg = _("Issued %d of %d unit(s).") % (success, len(self.unit_ids))
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
        """Return all issued units."""
        self.ensure_one()
        if self.state not in ('issued', 'partial_return'):
            raise UserError(_('Can only return issued sets.'))

        today = fields.Date.today()
        Movement = self.env['op.media.movement']
        success = 0
        errors = []

        for unit in self.unit_ids:
            move = Movement.search([
                ('media_unit_id', '=', unit.id),
                ('state', '=', 'issue'),
            ], limit=1, order='id desc')
            if move:
                move.return_media(today)
                success += 1
            else:
                errors.append(
                    _("No active movement found for %s") % unit.name)

        # Check if all returned
        remaining = Movement.search_count([
            ('media_unit_id', 'in', self.unit_ids.ids),
            ('state', '=', 'issue'),
        ])
        if remaining == 0:
            self.state = 'returned'
        elif success > 0:
            self.state = 'partial_return'

        msg = _("Returned %d of %d unit(s).") % (success, len(self.unit_ids))
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

    def action_reset_to_draft(self):
        """Reset returned set back to draft for re-issue."""
        self.ensure_one()
        if self.state != 'returned':
            raise UserError(_('Can only reset returned sets to draft.'))

        # Clear unit_ids for re-pick (they will be available after return)
        self.unit_ids = [(5, 0, 0)]
        self.state = 'draft'

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }