from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    charge_at_start = fields.Boolean(
        'Взнос при поступлении',
        help='Переносится из строки шаблона КП. Такие строки не попадают '
             'в подписку: по ним создаётся разовый счёт взноса.')
