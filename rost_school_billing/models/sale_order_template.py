from odoo import fields, models


class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'

    charge_at_start = fields.Boolean(
        'Взнос при поступлении',
        help="Разовый взнос: в подписку не попадает, выставляется "
             "отдельным счётом в приёмке.")

    def _is_entry_fee(self):
        """Строка взноса и в шаблоне КП — по товару/названию, на случай
        что флаг не выставлен."""
        self.ensure_one()
        name = f'{self.product_id.display_name or ""} {self.name or ""}'.lower()
        return 'вступительный взнос' in name

    def _prepare_order_line_values(self):
        """Нативное заполнение КП из шаблона: везём флаг взноса
        вместе со строкой, чтобы код подписки отличал её от месячных."""
        vals = super()._prepare_order_line_values()
        vals['charge_at_start'] = self.charge_at_start
        return vals


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    doc_clause35 = fields.Text(
        'Условия п. 3.7 договора',
        help="Текст пункта 3.7 договора с этим шаблоном КП: вступительный "
             "взнос, скидки и т.п. Наследуется в КП и в подписку — в "
             "договор попадает именно он. Суммы прописью в этом тексте "
             "ответственность менеджера (в графике платежей договора "
             "пропись формируется автоматически).")
