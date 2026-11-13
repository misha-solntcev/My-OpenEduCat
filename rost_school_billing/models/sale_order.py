from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    doc_clause35 = fields.Text(
        'Условия п. 3.5 договора',
        compute='_compute_doc_clause35', store=True, readonly=False,
        help="Из шаблона КП; правится в этом КП — попадёт в подписку "
             "и в договор.")

    @api.depends('sale_order_template_id')
    def _compute_doc_clause35(self):
        for order in self:
            if order.sale_order_template_id:
                order.doc_clause35 = \
                    order.sale_order_template_id.doc_clause35 or ''

    def _school_course_from_template(self):
        self.ensure_one()
        if not self.sale_order_template_id:
            return self.env['op.course']
        return self.env['op.course'].search([
            ('sale_order_template_id', '=', self.sale_order_template_id.id),
        ], limit=1)

    def _school_default_fees_start(self):
        """Старт оплаты — дата поступления (секретарь может поправить)."""
        return fields.Date.context_today(self)

    def _school_find_register(self, course):
        today = fields.Date.context_today(self)
        regs = self.env['op.admission.register'].search([
            ('state', '=', 'application'),
            ('start_date', '<=', today),
            ('end_date', '>=', today)])
        if not regs:
            raise UserError(_(
                'Нет активного набора приёмки (сегодня вне дат наборов). '
                'Создайте набор в Приёмка → Наборы.'))
        senior = (course.name or '')[:2] in ('10', '11')
        for r in regs:
            if ('Среднее' in r.name) == senior:
                return r
        return regs[:1]

    def _admission_action(self, admission):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'op.admission',
            'res_id': admission.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _school_find_batch(self, course):
        """Единственная параллель «А» класса: батч курса, активный
        на сегодня. Не находим — ошибка, батч заводится вручную."""
        today = fields.Date.context_today(self)
        batches = self.env['op.batch'].search(
            [('course_id', '=', course.id)])
        current = batches.filtered(
            lambda b: b.start_date and b.end_date
            and b.start_date <= today <= b.end_date)
        if not current:
            raise UserError(_(
                'Для класса «%s» нет параллели на текущий учебный год. '
                'Создайте её в Приёмка → Параллели '
                '(с датами, охватывающими сегодняшнюю дату).')
                % course.name)
        return current[-1]

    def action_open_admission(self):
        """Создать приёмку по результатам воронки (или открыть существующую).
        Данные ребёнка берутся из вкладки «Ученик» лида, плательщик —
        партнёр заказа, класс — из шаблона КП."""
        self.ensure_one()
        admission = self.env['op.admission'].search(
            [('sale_order_id', '=', self.id)], limit=1)
        if admission:
            return self._admission_action(admission)

        course = self._school_course_from_template()
        if not course:
            raise UserError(_(
                'Не удалось определить класс: у заказа нет шаблона КП, '
                'привязанного к карточке курса.'))
        lead = self.opportunity_id
        child_name = lead.child_name or ''
        if not child_name:
            raise UserError(_(
                'В лиде заказа не заполнено ФИО ребёнка '
                '(вкладка «Ученик»).'))
        if not lead.child_birth_date:
            raise UserError(_(
                'В лиде «%s» не заполнена дата рождения ребёнка. '
                'Заполните её на вкладке «Ученик» лида и повторите '
                'кнопку «Поступление».') % lead.name)
        email = self.partner_id.email or (lead.email_from or '')
        if not email:
            raise UserError(_(
                'У родителя %s не указан e-mail.') % self.partner_id.name)
        child_email = (lead.child_email or '').strip()
        if child_email and child_email.lower() == email.strip().lower():
            raise UserError(_(
                'Почта ученика в анкете совпадает с почтой родителя (%s). '
                'Запросите у семьи второй адрес или очистите «Email ученика» '
                'в лиде — тогда будет один аккаунт, родительский.') % email)
        words = child_name.split()
        vals = {
            'name': child_name,
            'last_name': words[0],
            'first_name': words[1] if len(words) > 1 else words[0],
            'middle_name': ' '.join(words[2:]),
            'birth_date': lead.child_birth_date,
            'gender': lead.child_gender or 'm',
            'email': email,
            'child_email': child_email or False,
            'single_parent_account': not child_email,
            'course_id': course.id,
            'register_id': self._school_find_register(course).id,
            'batch_id': self._school_find_batch(course).id,
            'prev_institute_id': lead.child_current_school or '',
            'relationship_id': lead.child_parent_relationship_id or False,
            'application_date': fields.Date.context_today(self),
            'fees_start_date': self._school_default_fees_start(),
            'partner_id': self.partner_id.id,
            'sale_order_id': self.id,
        }
        admission = self.env['op.admission'].create(vals)
        if lead.child_address and not self.partner_id.street:
            self.partner_id.write({'street': lead.child_address})
        return self._admission_action(admission)
