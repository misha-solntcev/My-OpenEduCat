from odoo import api, fields, models


class OpMediaUnit(models.Model):
    _name = "op.media.unit"
    _inherit = "mail.thread"
    _description = "Media Unit"
    _order = "name"

    name = fields.Char('Name', required=True)
    media_id = fields.Many2one('op.media', 'Media',
                               required=True, tracking=True)
    barcode = fields.Char('Barcode')
    movement_lines = fields.One2many(
        'op.media.movement', 'media_unit_id', 'Movements')
    state = fields.Selection(
        [('available', 'Available'), ('issue', 'Issued')],
        'State', default='available', tracking=True, index=True)
    media_type_id = fields.Many2one(related='media_id.media_type_id',
                                    store=True, string='Тип')
    course_ids = fields.Many2many(related='media_id.course_ids',
                                  string='Класс')
    subject_ids = fields.Many2many(related='media_id.subject_ids',
                                   string='Предмет')
    author_ids = fields.Many2many(related='media_id.author_ids',
                                  string='Автор')
    publisher_ids = fields.Many2many(related='media_id.publisher_ids',
                                     string='Издательство')
    isbn = fields.Char('ISBN Code')
    edition = fields.Char('Edition')
    x_issue_year = fields.Char('Issue Year')
    active = fields.Boolean(default=True)
    current_partner_id = fields.Many2one(
        'res.partner', 'Текущий ученик',
        compute='_compute_current_partner', store=True)

    _sql_constraints = [
        ('unique_name_barcode',
         'unique(barcode)',
         'Barcode must be unique per Media unit!'),
    ]

    @api.depends('movement_lines.partner_id', 'movement_lines.state')
    def _compute_current_partner(self):
        for rec in self:
            rec.current_partner_id = False
        if not self.ids:
            return
        # Get the latest issued movement per unit
        self.env['op.media.movement'].flush_model(['media_unit_id', 'state', 'partner_id'])
        self.env.cr.execute("""
            SELECT DISTINCT ON (m.media_unit_id) m.media_unit_id, m.partner_id
            FROM op_media_movement m
            WHERE m.media_unit_id IN %s AND m.state = 'issue'
            ORDER BY m.media_unit_id, m.id DESC
        """, (tuple(self.ids),))
        for unit_id, partner_id in self.env.cr.fetchall():
            if partner_id:
                self.browse(unit_id).current_partner_id = partner_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            x = self.env['ir.sequence'].next_by_code(
                'op.media.unit') or '/'
            vals['barcode'] = x
        return super(OpMediaUnit, self).create(vals_list)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if not name:
            return super().name_search(name, args, operator, limit)
        domain = ['|', ('name', operator, name), ('barcode', operator, name)]
        return super().name_search(name, args + domain, operator, limit)
