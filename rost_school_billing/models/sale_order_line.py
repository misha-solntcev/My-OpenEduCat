from odoo import api, fields, models

ENTRY_FEE_MARKER = 'вступительный взнос'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    charge_at_start = fields.Boolean(
        'Взнос при поступлении',
        help='Переносится из строки шаблона КП. Такие строки не попадают '
             'в подписку: по ним создаётся разовый счёт взноса.')

    def _is_entry_fee(self):
        """Строка вступительного взноса.

        Флаг charge_at_start мог потеряться (строку добавили в КП руками),
        поэтому узнаём взнос и по товару/названию — иначе он уедет в
        подписку месячной линией в конец графика.
        """
        self.ensure_one()
        name = f'{self.product_id.display_name or ""} {self.name or ""}'.lower()
        return ENTRY_FEE_MARKER in name

    @api.model_create_multi
    def create(self, vals_list):
        # Строка взноса, добавленная в КП вручную, вьюха не помечает
        # флагом; ставим его сами, чтобы счёт взноса выставлялся при
        # поступлении, а не уезжал в конец подписки.
        for vals in vals_list:
            if vals.get('charge_at_start') or not vals.get('product_id'):
                continue
            product = self.env['product.product'].browse(vals['product_id'])
            if product and ENTRY_FEE_MARKER in (product.display_name or '').lower():
                vals['charge_at_start'] = True
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'product_id' in vals:
            fee = self.filtered(
                lambda l: l._is_entry_fee() and not l.charge_at_start)
            if fee:
                super(SaleOrderLine, fee).write({'charge_at_start': True})
        return res

    @api.onchange('product_id')
    def _onchange_product_id_entry_fee(self):
        if self.product_id and self._is_entry_fee():
            self.charge_at_start = True
