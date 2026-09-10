# -*- coding: utf-8 -*-
# Разовая миграция: hw_material-вложения (старое хранение res_field)
# -> Many2many rel-таблица rost_hw_material_rel.
# Запуск на тесте/проде: odoo shell < migration_materials_m2m.py
# Идемпотентна: повторный запуск ничего не портит (skip если уже в rel).
import logging

_logger = logging.getLogger(__name__)

Att = env['ir.attachment'].sudo()
Asg = env['op.assignment'].sudo()

OLD_DOMAIN = [
    ('res_model', '=', 'op.assignment'),
    ('res_field', '=', 'hw_material'),
]

atts = Att.search(OLD_DOMAIN)
_logger.info("hw_material attachments: %d", len(atts))

linked = orphan = 0
for att in atts:
    asg = Asg.browse(att.res_id).exists()
    if not asg:
        orphan += 1
        _logger.warning("orphan attachment %s (assignment %s gone) — unlink",
                        att.id, att.res_id)
        att.unlink()
        continue
    if att.id in asg.material_ids.ids:
        linked += 1
        continue
    asg.write({'material_ids': [(4, att.id)]})
    linked += 1
    # res_field больше не нужен — очищаем, чтобы вложение стало «обычным».
    att.write({'res_field': False})

env.cr.commit()
_logger.info("linked: %d, orphans removed: %d — DONE", linked, orphan)
