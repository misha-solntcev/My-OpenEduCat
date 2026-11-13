# -*- coding: utf-8 -*-
"""Перенос xmlid при рефакторинге родителя (13.11.2026).

Записи (поля op.parent, поля-двойники op.admission, вьюхи родителя,
строка канбана в экшене) переезжают из rost_school_billing в
openeducat_parent / openeducat_admission. Если просто перенести <record>
в другой модуль, Odoo при -u создаст НОВЫЕ записи, а старые (вместе с
колонками полей — _process_end → ir.model.fields._drop_column) удалит.
Переименование module у существующих ir_model_data сохраняет res_id:
-u обновляет те же строки, дублей вьюх нет, колонки не трогаются,
порядок обновления модулей перестаёт иметь значение.

Запуск (до -u), из каталога addons:
    docker exec -i odoo-dev-odoo-1 odoo shell -d test4 \
        -c /etc/odoo/odoo.conf --no-http < scripts/migrate_parent_xmlids.py
"""
SRC = 'rost_school_billing'

MOVES = {
    'openeducat_parent': [
        # поля op.parent (личные данные + канбан)
        'field_op_parent__birth_date',
        'field_op_parent__passport_number',
        'field_op_parent__passport_issued_by',
        'field_op_parent__passport_issue_date',
        'field_op_parent__passport_dept_code',
        'field_op_parent__address_reg',
        'field_op_parent__address_home',
        'field_op_parent__image_1920',
        'field_op_parent__avatar_128',
        'field_op_parent__student_count',
        # вьюхи и строка канбана в экшене
        'view_op_parent_form_rost',
        'kanban_view_op_parent',
        'act_open_op_parent_view_kanban_rost',
    ],
    'openeducat_admission': [
        # поля-двойники приёмки + родство
        'field_op_admission__relationship_id',
        'field_op_admission__parent_birth_date',
        'field_op_admission__parent_passport_number',
        'field_op_admission__parent_passport_issued_by',
        'field_op_admission__parent_passport_issue_date',
        'field_op_admission__parent_passport_dept_code',
        'field_op_admission__parent_address_reg',
        'field_op_admission__parent_address_home',
    ],
}

IMD = env['ir.model.data'].sudo()
moved, skipped, clashes = 0, 0, 0

for dst_module, names in MOVES.items():
    for name in names:
        src = IMD.search([('module', '=', SRC), ('name', '=', name)], limit=1)
        dst = IMD.search([('module', '=', dst_module), ('name', '=', name)],
                         limit=1)
        if not src:
            if dst:
                print('  уже перенесено: %s.%s (res_id=%s)'
                      % (dst_module, name, dst.res_id))
            else:
                print('  НЕ НАЙДЕНО НИГДЕ: %s' % name)
            skipped += 1
            continue
        if dst:
            print('  КОНФЛИКТ: %s.%s уже есть (res_id=%s), в billing res_id=%s'
                  % (dst_module, name, dst.res_id, src.res_id))
            clashes += 1
            continue
        print('  %-52s %s.model=%s res_id=%s'
              % (name, src.model, src.model, src.res_id))
        src.write({'module': dst_module})
        moved += 1

env.cr.commit()
print('ИТОГО: перенесено %d, пропущено %d, конфликтов %d'
      % (moved, skipped, clashes))
