from odoo import _, api, fields, models
from odoo.exceptions import UserError
from markupsafe import Markup


class OpAdmission(models.Model):
    _inherit = 'op.admission'

    billing_partner_id = fields.Many2one(
        'res.partner', 'Плательщик',
        compute='_compute_billing_partner', store=True, readonly=False,
        help="Родитель из карточки ученика; если не указан — партнёр "
             "ученика.")
    entry_fee_invoice_id = fields.Many2one(
        'account.move', 'Счёт за вступительный взнос', copy=False)
    contract_ids = fields.One2many(
        'contract.contract', compute='_compute_contract_ids',
        string='Подписки')
    contract_count = fields.Integer(compute='_compute_contract_ids')
    billing_schedule_html = fields.Html(
        'График платежей', compute='_compute_billing_schedule_html')

    @api.depends('student_id', 'student_id.parent_ids',
                 'student_id.partner_id')
    def _compute_billing_partner(self):
        for admission in self:
            parent = admission.student_id.parent_ids[:1].name
            admission.billing_partner_id = (
                parent or admission.student_id.partner_id)

    @api.depends('student_id')
    def _compute_contract_ids(self):
        for admission in self:
            admission.contract_ids = admission.student_id.contract_ids
            admission.contract_count = len(admission.contract_ids)

    @api.depends('student_id', 'student_id.contract_ids',
                 'student_id.contract_ids.payment_schedule_html')
    def _compute_billing_schedule_html(self):
        for admission in self:
            contracts = admission.student_id.contract_ids
            parts = [c.payment_schedule_html for c in contracts
                     if c.payment_schedule_html]
            admission.billing_schedule_html = (
                Markup('<br/>'.join(str(p) for p in parts))
                if parts else Markup(''))

    def action_create_subscription(self):
        self.ensure_one()
        if not self.student_id:
            raise UserError(_('Ученик ещё не создан (подтвердите приёмку).'))
        return self.student_id.action_create_subscription(
            start_date=self.fees_start_date,
            partner=self.billing_partner_id or None)

    def action_create_entry_fee_invoice(self):
        self.ensure_one()
        if not self.student_id:
            raise UserError(_('Ученик ещё не создан.'))
        if self.entry_fee_invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.entry_fee_invoice_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        product = self.env['product.product'].search(
            [('name', 'ilike', 'Вступительный взнос')], limit=1)
        if not product:
            raise UserError(_(
                'Не найден товар «Вступительный взнос».'))
        account = (product.property_account_income_id
                   or product.categ_id.property_account_income_categ_id)
        if not account:
            raise UserError(_(
                'У товара «%s» и его категории не задан доходный счёт.')
                % product.name)
        partner = (self.billing_partner_id or self.student_id.partner_id)
        course = self.student_id._get_billing_course_detail().course_id
        pricelist = course.billing_pricelist_id
        price = product.lst_price or 0.0
        if pricelist:
            price = pricelist._get_product_price(
                product, 1, date=fields.Date.context_today(self))
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'ref': _('Вступительный взнос — %s') % self.student_id.name,
            'invoice_line_ids': [(0, 0, {
                'name': _('Вступительный взнос — %s')
                        % self.student_id.name,
                'product_id': product.id,
                'quantity': 1.0,
                'price_unit': price,
                'account_id': account.id,
            })],
        })
        self.entry_fee_invoice_id = invoice.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
