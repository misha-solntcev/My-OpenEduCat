from odoo import fields, models


class OpDay(models.Model):
    _name = 'op.day'
    _description = 'Day of Week'
    _order = 'sequence'

    name = fields.Char('Название', required=True, translate=True)
    code = fields.Char('Код', required=True)
    sequence = fields.Integer('Последовательность', default=10)
    fold = fields.Boolean('Свернуть пустые', default=False)