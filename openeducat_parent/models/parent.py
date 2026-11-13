###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpParent(models.Model):
    _name = "op.parent"
    _description = "Parent"
    _order = "name"

    name = fields.Many2one('res.partner', 'Name', required=True)
    user_id = fields.Many2one('res.users', string='User', store=True)
    student_ids = fields.Many2many('op.student', string='Student(s)')
    mobile = fields.Char(string='Mobile', related='name.mobile')
    active = fields.Boolean(default=True)
    relationship_id = fields.Many2one('op.parent.relationship',
                                      'Relation with Student', required=True)

    # ---- РОСТ: личные данные родителя (решение 12.11.2026) ----
    # Живут в SIS (op.parent), не в контактах: контакты остаются по
    # стандарту Odoo — имя, телефон, email. Источник токенов parent_*
    # для договоров — эти поля.
    birth_date = fields.Date('Дата рождения')
    passport_number = fields.Char(
        'Паспорт: серия и номер',
        help="Как в договоре, одним полем: «40 20 781577».")
    passport_issued_by = fields.Char('Паспорт: кем выдан')
    passport_issue_date = fields.Date('Паспорт: дата выдачи')
    passport_dept_code = fields.Char(
        'Паспорт: код подразделения',
        help="«780-006».")
    address_reg = fields.Char(
        'Адрес регистрации',
        help="Адрес регистрации по паспорту — для договора.")
    address_home = fields.Char(
        'Адрес фактического проживания',
        help="Домашний адрес — для договора.")

    # Канбан: аватар — фото контакта (одна точка правды, как у ученика
    # и учителя, которые наследуют res.partner через _inherits).
    # Поля related, а не stored: partner.image_1920 — несторовый
    # compute (avatar_mixin), store молча не сохранится.
    image_1920 = fields.Image(related='name.image_1920')
    avatar_128 = fields.Image(related='name.avatar_128')
    student_count = fields.Integer(
        'Детей', compute='_compute_student_count')

    def _compute_student_count(self):
        for parent in self:
            parent.student_count = len(parent.student_ids)

    _sql_constraints = [(
        'unique_parent',
        'unique(name)',
        'Can not create parent multiple times.!'
    )]

    @api.onchange('name')
    def _onchange_name(self):
        # user_id — АККАУНТ родителя (res.users, у которого
        # partner_id = name). res.partner.user_id — другое поле: менеджер
        # продаж, его CRM заполняет при создании контакта из лида, и
        # брать его за «у родителя есть аккаунт» нельзя (13.11.2026:
        # из-за этого родителям из воронки аккаунт не создавался вовсе).
        self.user_id = self.name.user_ids[:1]

    @api.model_create_multi
    def create(self, vals_list):
        res = super(OpParent, self).create(vals_list)
        for vals, rec in zip(vals_list, res):
            if vals.get('student_ids', False) and rec.user_id:
                user_ids = [student_id.user_id.id
                            for student_id in rec.student_ids
                            if student_id.user_id]
                rec.user_id.child_ids = [(6, 0, user_ids)]
        return res

    def write(self, vals):
        res = super(OpParent, self).write(vals)
        for rec in self:
            if vals.get('student_ids', False) and rec.user_id:
                usr_ids = [student_id.user_id.id
                           for student_id in rec.student_ids
                           if student_id.user_id]
                rec.user_id.child_ids = [(6, 0, usr_ids)]
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        for record in self:
            if record.user_id:
                record.user_id.child_ids = [(6, 0, [])]
        return super(OpParent, self).unlink()

    def create_parent_user(self):
        users_res = self.env['res.users']
        for record in self:
            if not record.name.email:
                raise ValidationError(_('Update parent email id first.'))
            # Аккаунт уже есть, если у контакта есть пользователи
            # (name.user_ids) — именно так, а не по name.user_id
            # (это менеджер продаж, см. _onchange_name).
            if not record.name.user_ids:
                # Матрица ROST: родитель = ВНУТРЕННИЙ пользователь с группой
                # «Родитель» (наследует Student). Портал-тип (share) не
                # используется; счета родитель смотрит на /my/invoices —
                # доступ к своим счетам дают ACL+правила группы в
                # rost_school_access (см. op_security.xml).
                groups_id = [(4, self.env.ref('base.group_user').id)]
                parent_group = self.env.ref(
                    'rost_school_access.group_op_parent_rost',
                    raise_if_not_found=False)
                if parent_group:
                    groups_id.append((4, parent_group.id))
                user_ids = [
                    parent.user_id.id for
                    parent in record.student_ids if parent.user_id]
                user_id = users_res.create({
                    'name': record.name.name,
                    'partner_id': record.name.id,
                    'login': record.name.email,
                    'is_parent': True,
                    'tz': self._context.get('tz'),
                    'groups_id': groups_id,
                    'child_ids': [(6, 0, user_ids)]
                })
                # res.partner.user_id (менеджер продаж) НЕ трогаем:
                # связь «родитель ↔ аккаунт» живёт в op.parent.user_id.
                record.user_id = user_id


class OpStudent(models.Model):
    _inherit = "op.student"

    parent_ids = fields.Many2many('op.parent', string='Parent')

    @api.model_create_multi
    def create(self, vals):
        res = super(OpStudent, self).create(vals)
        for values in vals:
            if values.get('parent_ids', False):
                for parent_id in res.parent_ids:
                    if parent_id.user_id:
                        user_ids = [student.user_id.id for student
                                    in parent_id.student_ids if student.user_id]
                        parent_id.user_id.child_ids = [(6, 0, user_ids)]
        return res

    def write(self, vals):
        res = super(OpStudent, self).write(vals)
        if vals.get('parent_ids', False):
            user_ids = []
            if self.parent_ids:
                for parent in self.parent_ids:
                    if parent.user_id:
                        user_ids = [parent.user_id.id for parent in parent.student_ids
                                    if parent.user_id]
                        parent.user_id.child_ids = [(6, 0, user_ids)]
            else:
                user_ids = self.env['res.users'].search([
                    ('child_ids', 'in', self.user_id.id)])
                for user_id in user_ids:
                    child_ids = user_id.child_ids.ids
                    child_ids.remove(self.user_id.id)
                    user_id.child_ids = [(6, 0, child_ids)]
        if vals.get('user_id', False):
            for parent_id in self.parent_ids:
                if not parent_id.user_id:
                    # У родителя может не быть аккаунта (режим «один
                    # аккаунт родителя», решение 12.11.2026) — обновлять
                    # child_ids не у кого.
                    continue
                child_ids = parent_id.user_id.child_ids.ids
                child_ids.append(vals['user_id'])
                parent_id.user_id.child_ids = [(6, 0, child_ids)]
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        for record in self:
            if record.parent_ids:
                for parent_id in record.parent_ids:
                    child_ids = parent_id.user_id.child_ids.ids
                    child_ids.remove(record.user_id.id)
                    parent_id.user_id.child_ids = [(6, 0, child_ids)]
        return super(OpStudent, self).unlink()

    def get_parent(self):
        action = self.env.ref('openeducat_parent.'
                              'act_open_op_parent_view').sudo().read()[0]
        action['domain'] = [('student_ids', 'in', self.ids)]
        return action


class OpSubjectRegistration(models.Model):
    _inherit = "op.subject.registration"

    @api.model_create_multi
    def create(self, vals):
        if self.env.user.child_ids:
            raise ValidationError(_('Invalid Action!\n Parent can not \
            create Subject Registration!'))
        return super(OpSubjectRegistration, self).create(vals)

    def write(self, vals):
        if self.env.user.child_ids:
            raise ValidationError(_('Invalid Action!\n Parent can not edit \
            Subject Registration!'))
        return super(OpSubjectRegistration, self).write(vals)
