# -*- coding: utf-8 -*-
# res.users: ученикам запрещено менять СЕБЕ фото, имя и email.
#
# Почему не record rules/ACL: ядро Odoo 18 разрешает любому пользователю
# писать сам на себя поля из SELF_WRITEABLE_FIELDS ('signature', 'action_id',
# 'company_id', 'email', 'name', 'image_1920', 'lang', 'tz') — в write()
# (base/models/res_users.py, ~740) такая запись уходит в self.sudo() и права
# вообще не проверяются. Кейс 2026-10-15: ученик (uid 159) сам сменил себе
# аватарку через диалог «Настройки». Единственная точка закрытия — write().
#
# Гейт срабатывает только на запись САМОГО СЕБЯ (self == self.env.user):
# админ редактирует записи учеников как раньше. env.su (код, cron, sudo())
# не трогаем. Админ-исключение — base.group_erp_manager: админ с ролью
# «Ученик» сохраняет возможность менять себе фото/имя/почту.
#
# Группа «Родитель» (group_op_parent_rost) имплисит group_op_students, но
# родители ИСКЛЮЧЕНЫ из гейта (решение 2026-10-29): им можно менять
# своё фото/имя/email.
from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.translate import _

# Остальные поля из SELF_WRITEABLE_FIELDS (lang, tz, notification_type,
# action_id, company_id) остаются самостоятельными: UI-путь к ним закрыт
# скрытием вкладки «Предпочтения» (см. custom_views.xml), а прямые записи
# безвредны. signature в списке — подпись письма это персональный контент.
STUDENT_LOCKED_SELF_FIELDS = ('image_1920', 'name', 'email', 'signature')


class Users(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        if (
            not self.env.su
            and set(vals) & set(STUDENT_LOCKED_SELF_FIELDS)
            and self == self.env.user
            and self.env.user.has_group('openeducat_core.group_op_students')
            and not self.env.user.has_group('rost_school_access.group_op_parent_rost')
            and not self.env.user.has_group('base.group_erp_manager')
        ):
            raise AccessError(_(
                'Ученикам нельзя менять свои фото, имя, email и подпись — '
                'обратитесь к администратору школы.'
            ))
        return super().write(vals)

    # UI-полировка к write()-гейту. Почему именно так:
    #  - fields_get(readonly=True) НЕ работает: в диалоге «Настройки» у полей
    #    явный readonly="0" в arch, явный атрибут узла перекрывает метаданные
    #    поля (проверено 2026-10-29 под учеником);
    #  - узловые groups тоже не годятся: get_views не вырезает группы-узлы
    #    (в браузере получались три дубля поля), groups_id на унаследованной
    #    вьюхе запрещён ParseError'ом, у has_groups нет булевых and/or;
    #  - а вот выражение в readonly по ПОЛЮ ЗАПИСИ работает — прецеденты в
    #    этой самой вьюхе: odoobot_state readonly="not can_edit" и кнопка
    #    языка с is_system. Значение поля сервер считает под сессией
    #    пользователя (depends_context('uid')), кэш arch этому не мешает.
    rost_self_edit_locked = fields.Boolean(
        compute='_compute_rost_self_edit_locked')

    @api.depends_context('uid')
    def _compute_rost_self_edit_locked(self):
        for user in self:
            user.rost_self_edit_locked = (
                user.has_group('openeducat_core.group_op_students')
                and not user.has_group('rost_school_access.group_op_parent_rost')
                and not user.has_group('base.group_erp_manager')
            )
