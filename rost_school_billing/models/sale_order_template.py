from odoo import fields, models


class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'

    charge_at_start = fields.Boolean(
        'Взнос при поступлении',
        help="Разовый взнос: в подписку не попадает, выставляется "
             "отдельным счётом по кнопке в приёмке.")
