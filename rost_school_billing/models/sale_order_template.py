from odoo import fields, models


class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'

    charge_at_start = fields.Boolean(
        'Взнос при поступлении',
        help="Разовый взнос: в подписку не попадает, выставляется "
             "отдельным счётом в приёмке.")

    def _prepare_order_line_values(self):
        """Нативное заполнение КП из шаблона: везём флаг взноса
        вместе со строкой, чтобы код подписки отличал её от месячных."""
        vals = super()._prepare_order_line_values()
        vals['charge_at_start'] = self.charge_at_start
        return vals
