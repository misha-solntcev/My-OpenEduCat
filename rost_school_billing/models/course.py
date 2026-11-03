from odoo import fields, models


class OpCourse(models.Model):
    _inherit = 'op.course'

    sale_order_template_id = fields.Many2one(
        'sale.order.template', 'Шаблон КП (график оплаты)',
        help="Строки шаблона определяют помесячный график: продукт, "
             "количество месяцев, цена берётся из прайс-листа биллинга.")
    billing_pricelist_id = fields.Many2one(
        'product.pricelist', 'Прайс-лист биллинга',
        help="Цены подписки берутся из этого прайс-листа (на учебный год).")
