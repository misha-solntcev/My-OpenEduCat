from odoo import api, fields, models


class OpStudent(models.Model):
    _inherit = "op.student"

    library_card_id = fields.Many2one('op.library.card', 'Library Card')
    media_movement_lines = fields.One2many(
        'op.media.movement', 'student_id', 'Movements')
    media_movement_lines_count = fields.Integer(compute='_compute_media_movement_lines')

    def _compute_media_movement_lines(self):
        for rec in self:
            rec.media_movement_lines_count = 0
        if not self.ids:
            return
        self.env['op.media.movement'].flush_model(['student_id'])
        data = self.env['op.media.movement'].read_group(
            [('student_id', 'in', self.ids)],
            ['student_id', '__count'],
            ['student_id'],
        )
        count_map = {r['student_id'][0]: r.get('student_id_count', r.get('__count', 0)) for r in data}
        for rec in self:
            rec.media_movement_lines_count = count_map.get(rec.id, 0)

    def count_media_movement_lines(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Media Movement',
            'view_mode': 'list,form',
            'res_model': 'op.media.movement',
            'domain': [('student_id', '=', self.id)],
            'target': 'current',
        }
