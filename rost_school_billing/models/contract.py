import re
from collections import Counter

from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import doc_engine
from .doc_engine import (
    SUMMER_MONTHS, amount_words, date_iso, date_quoted, fmt_amount,
    month_year_gen, fio_gen,
)


class ContractContract(models.Model):
    _inherit = 'contract.contract'

    # Методы генерации документов подключаются присваиванием функций:
    # _inherit-список с абстрактным mixin сдвигает setup-порядок моделей,
    # и One2many op.student.contract_ids падает раньше, чем у
    # contract.contract появляются поля (KeyError: student_id).
    action_generate_doc = doc_engine.action_generate_doc
    _rost_company_ctx = doc_engine._rost_company_ctx
    _rost_student_ctx = doc_engine._rost_student_ctx
    _rost_parent_ctx = doc_engine._rost_parent_ctx

    student_id = fields.Many2one(
        'op.student', 'Ученик', index=True, tracking=True,
        help="Ученик, за обучение которого выставляются счета.")
    doc_number = fields.Char(
        'Номер договора', copy=False, index=True,
        help="Пусто — при генерации возьмётся следующий из "
             "последовательности. Вписанный вручную используется как есть "
             "(бумажный журнал), дубли не допускаются.")
    doc_date = fields.Date('Дата договора', copy=False)
    doc_clause35 = fields.Text(
        'Условия п. 3.5',
        help="Текст пункта 3.5 договора: взнос/скидки. Заполняется из "
             "КП при создании подписки, перед генерацией можно поправить.")
    doc_file_ids = fields.Many2many(
        'ir.attachment', compute='_compute_doc_file_ids',
        string='Файлы договора')
    payment_schedule_html = fields.Html(
        'График платежей', compute='_compute_payment_schedule_html')

    @api.constrains('doc_number')
    def _check_doc_number_uniq(self):
        for rec in self:
            if not rec.doc_number:
                continue
            dup = self.search_count([
                ('doc_number', '=', rec.doc_number),
                ('id', '!=', rec.id)])
            if dup:
                raise UserError(_(
                    'Договор с номером «%s» уже существует.') % rec.doc_number)

    def _compute_doc_file_ids(self):
        for rec in self:
            rec.doc_file_ids = self.env['ir.attachment'].search([
                ('res_model', '=', 'contract.contract'),
                ('res_id', '=', rec.id)])

    def _rost_doc_context(self):
        """Полный контекст токенов: company_*, student_*, parent_*,
        contract_*, doc_*."""
        self.ensure_one()
        ctx = self._rost_company_ctx()
        student = self.student_id
        parent_partner = self.partner_id
        relationship = ''
        if student and student.parent_ids:
            op_parent = student.parent_ids[:1]
            parent_partner = op_parent.name
            relationship = op_parent.relationship_id.name or ''
        ctx.update(self._rost_student_ctx(student))
        ctx.update(self._rost_parent_ctx(parent_partner, relationship))
        ctx.update(self._rost_contract_ctx())
        return ctx

    def _rost_contract_ctx(self):
        """Токены contract_* из линий подписки (источник истины по ценам,
        тот же, по которому cron выставляет счета)."""
        self.ensure_one()
        lines = self.contract_line_ids.filtered(
            lambda l: not l.display_type and not l.is_canceled
            and l.date_start and l.price_unit).sorted('date_start')
        main = lines.filtered(
            lambda l: l.date_start.month not in SUMMER_MONTHS)
        summer = lines - main
        total = sum(l.quantity * l.price_unit
                    * (1 - (l.discount or 0.0) / 100.0) for l in lines)
        price_main = (Counter(l.price_unit for l in main).most_common(1)[0][0]
                      if main else 0.0)
        price_summer = (Counter(
            l.price_unit for l in summer).most_common(1)[0][0]
            if summer else price_main)
        if lines:
            first = fields.Date.to_date(lines[0].date_start)
            school_year_start = (first.year if first.month >= 9
                                 else first.year - 1)
            school_year = f'{school_year_start}-{school_year_start + 1}'
            ends = [l.date_end for l in lines if l.date_end]
            if ends:
                last_year = max(ends).year
                valid_until = date_quoted(fields.Date.to_date(
                    fields.Date.end_of(
                        fields.Date.to_date(f'{last_year}-08-01'), 'month')))
            else:
                valid_until = ''
        else:
            school_year, valid_until = '', ''
        doc_date = self.doc_date
        yy = f'{doc_date.year % 100:02d}' if doc_date else ''
        main_first = (fields.Date.to_date(main[0].date_start) if main
                      else None)
        main_last = (fields.Date.to_date(main[-1].date_start) if main
                     else None)
        summer_first = (fields.Date.to_date(summer[0].date_start) if summer
                        else None)
        summer_names = {
            6: 'июнь', 7: 'июль', 8: 'август'}
        summer_list = (
            ', '.join(summer_names[l.date_start.month] for l in summer)
            + (f' {summer_first.year} года' if summer_first else '')
            if summer else '')
        return {
            'contract_number': self.doc_number or '',
            'contract_number_full':
                f'{self.doc_number} /01-{yy}' if self.doc_number and yy
                else '',
            'contract_year_short': yy,
            'contract_date_quoted': date_quoted(doc_date),
            'contract_year': school_year,
            'contract_valid_until_quoted': valid_until,
            'contract_price_year_fmt': fmt_amount(total),
            'contract_price_year_words': amount_words(total),
            'contract_main_months_n': str(len(main)),
            'contract_main_range': (
                f'с {month_year_gen(main_first)} '
                f'по {month_year_gen(main_last)}'
                if main_first and main_last else ''),
            'contract_month_main_fmt': fmt_amount(price_main),
            'contract_month_main_words': amount_words(price_main),
            'contract_summer_months_n': str(len(summer)),
            'contract_summer_list': summer_list,
            'contract_month_summer_fmt': fmt_amount(price_summer),
            'contract_month_summer_words': amount_words(price_summer),
            'contract_clause35': self.doc_clause35 or '',
            'doc_date_quoted': date_quoted(doc_date),
        }

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
