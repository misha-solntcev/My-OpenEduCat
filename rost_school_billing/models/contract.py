from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from odoo import fields, models


class ContractContract(models.Model):
    _inherit = 'contract.contract'

    student_id = fields.Many2one(
        'op.student', 'Ученик', index=True, tracking=True,
        help="Ученик, за обучение которого выставляются счета.")
    payment_schedule_html = fields.Html(
        'График платежей', compute='_compute_payment_schedule_html')

    def _compute_payment_schedule_html(self):
        for contract in self:
            rows = []
            total = 0.0
            for line in contract.contract_line_ids.sorted('date_start'):
                if (line.display_type or line.is_canceled
                        or not line.date_start):
                    continue
                step = line.recurring_interval or 1
                d = line.date_start
                guard = 0
                invoices = self.env['account.move'].search([
                    ('line_ids.contract_line_id', '=', line.id),
                    ('move_type', '=', 'out_invoice')],
                    order='invoice_date, id')
                idx = 0
                while (not line.date_end or d <= line.date_end) and guard < 60:
                    amount = (line.quantity * line.price_unit
                              * (1 - (line.discount or 0.0) / 100.0))
                    total += amount
                    invoice = invoices[idx] if idx < len(invoices) else None
                    if invoice:
                        idx += 1
                    if invoice:
                        if invoice.payment_state == 'paid':
                            status = ('<span class="text-success">оплачен '
                                      '(%s)</span>' % (invoice.name or ''))
                        else:
                            status = ('<span class="text-muted">%s %s'
                                      '</span>' % (
                                          'черновик' if invoice.state
                                          == 'draft' else 'выставлен',
                                          invoice.name or ''))
                    elif d == line.recurring_next_date:
                        status = '<span class="text-info">следующий</span>'
                    else:
                        status = ('<span class="text-success">'
                                  'ожидается</span>')
                    rows.append(
                        '<tr><td>%s</td><td>%s</td>'
                        '<td class="text-end">%.2f</td>'
                        '<td class="text-end">%s</td></tr>'
                        % (d.strftime('%m.%Y'), line.name[:60], amount,
                           status))
                    d += relativedelta(months=step)
                    guard += 1
            html = (
                '<table class="table table-sm"><thead><tr>'
                '<th>Месяц</th><th>Услуга</th>'
                '<th class="text-end">Сумма</th>'
                '<th class="text-end">Статус</th></tr></thead>'
                '<tbody>%s</tbody><tfoot><tr>'
                '<td colspan="2" class="text-end"><strong>Итого:</strong>'
                '</td><td class="text-end"><strong>%.2f</strong></td>'
                '<td></td></tr></tfoot></table>'
                % (''.join(rows), total))
            contract.payment_schedule_html = Markup(html)
