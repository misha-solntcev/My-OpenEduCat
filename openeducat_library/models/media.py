##############################################################################
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
##############################################################################

from odoo import fields, models, api


class OpMedia(models.Model):
    _name = "op.media"
    _description = "Media Details"
    _inherit = "mail.thread"
    _order = "name"

    name = fields.Char('Title', size=128, required=True)
    isbn = fields.Char('ISBN Code', size=64)
    tags = fields.Many2many('op.tag', string='Tag(s)')
    author_ids = fields.Many2many(
        'op.author', string='Author(s)', required=True)
    edition = fields.Char('Edition')
    description = fields.Text('Description')
    publisher_ids = fields.Many2many(
        'op.publisher', string='Publisher(s)', required=True)
    course_ids = fields.Many2many('op.course', string='Course')
    movement_line = fields.One2many('op.media.movement', 'media_id',
                                    'Movements')
    subject_ids = fields.Many2many(
        'op.subject', string='Subjects')
    queue_ids = fields.One2many('op.media.queue', 'media_id', 'Media Queue')
    unit_ids = fields.One2many('op.media.unit', 'media_id', 'Units')
    media_type_id = fields.Many2one('op.media.type', 'Media Type')
    active = fields.Boolean(default=True)
    x_image_128 = fields.Image('Image', max_width=128, max_height=128)

    # Вычисляемые поля для отображения количества экземпляров
    total_units = fields.Integer('Total Units', compute='_compute_unit_counts',
                                 store=True)
    issued_units = fields.Integer('Issued Units', compute='_compute_unit_counts',
                                  store=True)
    available_units = fields.Integer('Available Units', compute='_compute_unit_counts',
                                     store=True)
    unit_barcode = fields.Char('Unit Barcodes', compute='_compute_unit_barcode',
                               store=True, help='Concatenated barcodes of all units')

    @api.depends('unit_ids', 'unit_ids.state')
    def _compute_unit_counts(self):
        for record in self:
            record.total_units = 0
            record.issued_units = 0
            record.available_units = 0
        if not self.ids:
            return
        # Total units per media
        total_data = self.env['op.media.unit'].read_group(
            [('media_id', 'in', self.ids)],
            ['media_id'],
            ['media_id'],
        )
        total_map = {r['media_id'][0]: r['__count'] for r in total_data}
        # Units per media grouped by state
        state_data = self.env['op.media.unit'].read_group(
            [('media_id', 'in', self.ids)],
            ['media_id', 'state'],
            ['media_id', 'state'],
            lazy=False,
        )
        state_map = {}
        for r in state_data:
            mid = r['media_id'][0]
            if mid not in state_map:
                state_map[mid] = {}
            state_map[mid][r['state']] = r['__count']
        for rec in self:
            rec.total_units = total_map.get(rec.id, 0)
            states = state_map.get(rec.id, {})
            rec.issued_units = states.get('issue', 0)
            rec.available_units = states.get('available', 0)

    @api.depends('unit_ids', 'unit_ids.barcode')
    def _compute_unit_barcode(self):
        for record in self:
            record.unit_barcode = ', '.join(
                record.unit_ids.mapped('barcode'))

    _sql_constraints = [
        ('unique_name_isbn',
         'unique(isbn)',
         'ISBN code must be unique per media!'),
    ]
