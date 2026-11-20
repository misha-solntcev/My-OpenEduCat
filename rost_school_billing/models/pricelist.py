from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    rost_study_form = fields.Selection(
        [('regular', 'Очная'), ('distance', 'Дистанционная (ЭОС)')],
        'Форма обучения', default='regular', required=True,
        help="Попадает в п. 1.1 договора: «форма обучения – …».\n"
             "Дистанционная печатается как «дистанционная, с "
             "использованием электронной образовательной среды».")
