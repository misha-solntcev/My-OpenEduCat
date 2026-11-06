from datetime import date

from dateutil.relativedelta import relativedelta
from odoo import _, fields, models
from odoo.exceptions import UserError


class OpStudent(models.Model):
    _inherit = 'op.student'

    contract_ids = fields.One2many(
        'contract.contract', 'student_id', string='Подписки на обучение')
    contract_count = fields.Integer(compute='_compute_contract_count')

    def _compute_contract_count(self):
        for student in self:
            student.contract_count = len(student.contract_ids)

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Подписки'),
            'res_model': 'contract.contract',
            'view_mode': 'tree,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    def _get_billing_course_detail(self):
        self.ensure_one()
        running = self.course_detail_ids.filtered(
            lambda c: c.state == 'running')
        today = fields.Date.context_today(self)
        current = running.filtered(
            lambda c: c.academic_years_id.start_date <= today
            <= c.academic_years_id.end_date)
        return current[:1] or running[:1] or self.course_detail_ids[:1]

    def action_create_subscription(self, start_date=None, partner=None,
                                   order=None):
        """Подписка на обучение. Источник строк: подтверждённый заказ
        воронки (order) либо шаблон КП + прайс-лист курса (старый путь).
        Идемпотентно: ученики с подпиской пропускаются."""
        created = self.env['contract.contract']
        for student in self:
            if student.contract_count:
                continue
            detail = student._get_billing_course_detail()
            course = detail.course_id
            if not course:
                raise UserError(_(
                    'У ученика %s не указан курс.') % student.name)
            start = (start_date or detail.fees_start_date
                     or fields.Date.context_today(self))
            billing_partner = partner or student.parent_ids[:1].name \
                or student.partner_id
            if not billing_partner:
                raise UserError(_(
                    'Не определён плательщик для ученика %s.')
                    % student.name)
            if order and order.state != 'sale':
                raise UserError(_(
                    'Заказ %s не подтверждён — сначала завершите КП '
                    'в Продажах.') % order.name)
            line_vals = []
            month_cursor = 0
            template = pricelist = None
            if order:
                pricelist = order.pricelist_id or course.billing_pricelist_id
                src_lines = order.order_line
            else:
                template = course.sale_order_template_id
                pricelist = course.billing_pricelist_id
                if not template or not pricelist:
                    raise UserError(_(
                        'Для курса «%s» не заданы шаблон КП и прайс-лист '
                        'биллинга (карточка курса, раздел «Биллинг»).')
                        % course.name)
                src_lines = template.sale_order_template_line_ids
            # Линии подписки = календарные месяцы по 1-м числам, отсчитанные
            # подряд от месяца даты начала оплаты (fees_start_date):
            # пакет «N месяцев» даёт ровно N месяцев занятий от поступления
            # (пришла 5.11 на 3 мес → ноя, дек, янв); задним числом
            # (старт 1.09, годовой шаблон) график ложится сент..август, а
            # черновик за наступившие месяцы создаётся сразу — доначисление.
            anchor = date(start.year, start.month, 1)
            for src in src_lines:
                if src.display_type or src.charge_at_start \
                        or not src.product_uom_qty:
                    continue
                months = int(src.product_uom_qty)
                if order:
                    price = src.price_unit
                    discount = src.discount
                else:
                    price = pricelist._get_product_price(
                        src.product_id, 1, date=start)
                    discount = 0.0
                for i in range(months):
                    m_start = anchor + relativedelta(
                        months=month_cursor + i)
                    m_end = (m_start + relativedelta(months=1)
                             - relativedelta(days=1))
                    line_vals.append((0, 0, {
                        'name': src.product_id.display_name,
                        'product_id': src.product_id.id,
                        'quantity': 1,
                        'uom_id': src.product_id.uom_id.id,
                        'price_unit': price,
                        'discount': discount,
                        'automatic_price': False,
                        'date_start': max(m_start, start),
                        'date_end': m_end,
                        'recurring_rule_type': 'monthly',
                        'recurring_interval': 1,
                        'recurring_invoicing_type': 'pre-paid',
                        'recurring_invoicing_offset': 0,
                    }))
                month_cursor += months
            if not line_vals:
                raise UserError(_(
                    'В шаблоне «%s» нет строк для подписки.')
                    % template.name)
            contract = self.env['contract.contract'].create({
                'name': _('Обучение: %s (%s)')
                        % (student.name, course.name),
                'partner_id': billing_partner.id,
                'student_id': student.id,
                'contract_type': 'sale',
                'generation_type': 'invoice',
                'date_start': start,
                'date': start,
                'pricelist_id': pricelist.id,
                'line_recurrence': True,
                'recurring_rule_type': 'monthly',
                'recurring_interval': 1,
                'recurring_invoicing_type': 'pre-paid',
                'contract_line_ids': line_vals,
            })
            created |= contract
        if not created:
            return None
        # Черновики за просроченные (и наступившие) месяцы — сразу в момент
        # создания подписки: один счёт на подписку со всеми линиями, у которых
        # recurring_next_date <= сегодня, invoice_date = сегодня. Будущие
        # месяцы (включая летние по 1-м числам) остаются за дневным cron.
        created._recurring_create_invoice(
            date_ref=fields.Date.context_today(self))
        if len(created) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'contract.contract',
                'res_id': created.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Созданные подписки'),
            'res_model': 'contract.contract',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created.ids)],
        }
