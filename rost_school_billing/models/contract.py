import re
from collections import Counter

from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import doc_engine
from .doc_engine import (
    MONTHS_GEN, SUMMER_MONTHS, amount_words, date_iso, date_quoted,
    fmt_amount, month_year_gen, month_year_acc, fio_gen, plural_ru,
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
        'Условия п. 3.7',
        help="Текст пункта 3.7 договора: взнос/скидки. Заполняется из "
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
        # Заказчик — сторона договора (partner_id), а не «первый родитель»
        # из карточки ученика: иначе договор/допсоглашение называют
        # представителем не того человека, с кем заключён договор.
        partner = self.partner_id
        op_parent_model = self.env['op.parent']
        # 13.11.2026 контакт в op.parent переехал из name в partner_id;
        # поддерживаем обе схемы, пока ветки не сведены.
        contact_field = ('partner_id' if 'partner_id' in op_parent_model._fields
                         else 'name')
        op_parent = (op_parent_model.search(
            [(contact_field, '=', partner.id)], limit=1) if partner
            else op_parent_model)
        relationship = op_parent.relationship_id.name or ''
        ctx.update(self._rost_student_ctx(student))
        ctx.update(self._rost_parent_ctx(
            op_parent, relationship, partner=partner))
        ctx.update(self._rost_contract_ctx())
        return ctx

    def _rost_contract_ctx(self):
        """Токены contract_* из линий подписки (источник истины по ценам,
        тот же, по которому cron выставляет счета)."""
        self.ensure_one()

        def amount(line):
            return (line.quantity * line.price_unit
                    * (1 - (line.discount or 0.0) / 100.0))

        lines = self.contract_line_ids.filtered(
            lambda l: not l.display_type and not l.is_canceled
            and l.date_start and l.price_unit).sorted('date_start')
        # Вступительный взнос — разовый платёж, а не учебный месяц. В
        # подписке он иногда оказывается отдельной линией (флаг
        # charge_at_start теряется при ручной правке КП): в график
        # п. 3.3 он не входит, его сумма печатается отдельно в п. 3.5.
        fee_lines = lines.filtered(
            lambda l: 'вступительный взнос' in (l.name or '').lower())
        months = lines - fee_lines
        main = months.filtered(
            lambda l: l.date_start.month not in SUMMER_MONTHS)
        summer = months - main
        # Первый месяц при поступлении не с 1-го числа — неполный: его
        # сумма меньше месячной и в «N равных долей» не входит.
        partial = main.filtered(lambda l: l.date_start.day != 1)
        full = main - partial
        if not full:
            # Подписка из одного неполного месяца: описываем его как
            # единственный платёж, отдельный абзац не нужен.
            full = main
            partial = main.browse()
        total = sum(amount(l) for l in lines)
        prices = Counter(round(amount(l), 2) for l in full)
        price_main = prices.most_common(1)[0][0] if prices else 0.0
        full_months = full.filtered(
            lambda l: round(amount(l), 2) == price_main)
        price_summer = (Counter(
            round(amount(l), 2) for l in summer).most_common(1)[0][0]
            if summer else price_main)
        first_main = full_months or main
        partial_line = partial[:1]
        partial_amount = 0.0
        partial_range = ''
        if partial_line:
            partial_amount = amount(partial_line)
            p_start = fields.Date.to_date(partial_line.date_start)
            p_end = fields.Date.to_date(partial_line.date_end or p_start)

            def _long(d):
                return (f'{d.day} {MONTHS_GEN[d.month - 1]} {d.year} года')
            partial_range = f'с {_long(p_start)} по {_long(p_end)}'
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
        main_first = (fields.Date.to_date(first_main[0].date_start)
                      if first_main else None)
        main_last = (fields.Date.to_date(first_main[-1].date_start)
                     if first_main else None)
        summer_first = (fields.Date.to_date(summer[0].date_start) if summer
                        else None)
        summer_last = (fields.Date.to_date(summer[-1].date_start) if summer
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
            'contract_main_months_n': str(len(full_months)),
            'contract_main_months_word': plural_ru(
                len(full_months), 'месяца', 'месяцев', 'месяцев'),
            'contract_main_range': (
                f'с {month_year_gen(main_first)} года '
                f'по {month_year_acc(main_last)} года'
                if main_first and main_last else ''),
            'contract_month_main_fmt': fmt_amount(price_main),
            'contract_month_main_words': amount_words(price_main),
            'contract_summer_months_n': str(len(summer)),
            'contract_summer_months_word': plural_ru(
                len(summer), 'месяца', 'месяцев', 'месяцев'),
            'contract_summer_list': summer_list,
            'contract_summer_range': (
                f'с {month_year_gen(summer_first)} года '
                f'по {month_year_acc(summer_last)} года'
                if summer_first and summer_last else ''),
            'contract_month_summer_fmt': fmt_amount(price_summer),
            'contract_month_summer_words': amount_words(price_summer),
            # Неполный первый месяц: пустые токены = блок в шаблоне
            # исчезает целиком (docxtpl {%p if ... %}).
            'contract_partial_range': partial_range,
            'contract_partial_amount_fmt': (
                fmt_amount(partial_amount) if partial_line else ''),
            'contract_partial_amount_words': (
                amount_words(partial_amount) if partial_line else ''),
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
