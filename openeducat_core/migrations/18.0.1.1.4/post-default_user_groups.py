"""Post-migration: убрать чужие права из шаблона пользователя по умолчанию.

Новый пользователь, созданный без явного groups_id, наследует
res.users._default_groups() = base.default_user.groups_id. Запись в base
помечена noupdate, поэтому правка через XML на существующей базе не
применяется — чистим здесь.

Оставляем только внутреннего пользователя; менеджерские/бухгалтерские
права выдаются явно.
"""

from odoo import api, SUPERUSER_ID

KEEP_XMLIDS = ['base.group_user']


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    template = env.ref('base.default_user', raise_if_not_found=False)
    if not template:
        print('⚠ base.default_user не найден, шаблон не чистим')
        return
    keep = env['res.groups']
    for xmlid in KEEP_XMLIDS:
        grp = env.ref(xmlid, raise_if_not_found=False)
        if grp:
            keep |= grp
    if not keep:
        print('⚠ base.group_user не найден, шаблон не чистим')
        return
    current = template.sudo().groups_id
    extra = current - keep
    if extra:
        ext = extra.get_external_id()
        names = sorted(ext.get(g.id) or 'id:%s' % g.id for g in extra)
        print('Шаблон по умолчанию: снимаем %s групп(ы): %s'
              % (len(extra), ', '.join(names)))
        template.sudo().write({'groups_id': [(6, 0, keep.ids)]})
    print('Шаблон по умолчанию: %s групп(ы)'
          % len(template.sudo().groups_id))
