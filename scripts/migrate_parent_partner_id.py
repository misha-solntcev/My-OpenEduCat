# -*- coding: utf-8 -*-
"""Миграция op.parent: m2o ``name`` -> ``partner_id`` + related char ``name``.

ВЫПОЛНЯТЬ СТРОГО ДО ``-u openeducat_parent`` (и до -u любого модуля,
который использует op.parent).

Зачем нужен скрипт, а не «пусть Odoo сам при -u»
------------------------------------------------
Odoo сопоставляет поля с ir_model_fields по паре (model, name) — не по xmlid.
Если просто обновить модуль, то:
  * для нового поля partner_id не найдётся строка в ir_model_fields —
    Odoo создаст её и создаст новую колонку partner_id;
  * старая строка ir_model_fields (name, many2one) окажется «лишней» и в
    процессе -u будет удалена вместе с колонкой name — а колонку name к
    этому моменту создаст уже новое char-поле (related store=True).
На test4 это 118 родителей, на проде 119 — все потеряли бы связь с
контактом. Переименование колонки — операция над метаданными: данные не
копируются и не теряются, простой минимален.

Что делает скрипт
-----------------
1. Снимает CONSTRAINT op_parent_unique_parent (уникальность переезжает на
   partner_id; -u создаст constraint заново из _sql_constraints модели —
   _add_sql_constraints сравнивает определение и пересоздаёт).
2. RENAME COLUMN name -> partner_id (FK и индекс остаются валидными),
   переименовывает FK op_parent_name_fkey -> op_parent_partner_id_fkey.
3. UPDATE ir_model_fields: name -> partner_id (ровно ОДНА строка, base-поле).
   Через ORM это запрещено: IrModelFields.write кидает UserError на полях
   state='base' и вдобавок сам пытается переименовать колонку (а она уже
   переименована). Поэтому здесь и только здесь — SQL.
4. ir_model_data: xmlid field_op_parent__name -> field_op_parent__partner_id.
   Без этого _process_end удалит xmlid «исчезнувшего» поля, а вместе с ним
   (если xmlid единственный) и саму запись ir_model.fields.
5. Коммит и контрольные числа до/после.

Повторный запуск безопасен: на уже мигрированной базе печатает «УЖЕ
МИГРИРОВАНО» и ничего не меняет.

Откат: ALTER TABLE op_parent RENAME COLUMN partner_id TO name; (обратный
RENAME) + git revert + -u.

Запуск из каталога addons:
    docker exec -i odoo-dev-odoo-1 odoo shell -d test4 \
        -c /etc/odoo/odoo.conf --no-http < scripts/migrate_parent_partner_id.py
"""
import sys

TABLE = 'op_parent'
MODEL = 'op.parent'
MODULE = 'openeducat_parent'
OLD_COL, NEW_COL = 'name', 'partner_id'
OLD_XMLID = 'field_op_parent__name'
NEW_XMLID = 'field_op_parent__partner_id'
OLD_FK, NEW_FK = 'op_parent_name_fkey', 'op_parent_partner_id_fkey'
OLD_CONSTRAINT = 'op_parent_unique_parent'


def out(msg):
    sys.stdout.write(str(msg) + '\n')
    sys.stdout.flush()


def one(sql, params=None):
    cr.execute(sql, params or ())
    row = cr.fetchone()
    return row[0] if row else None


def column(cr, name):
    cr.execute("""
        SELECT data_type FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (TABLE, name))
    row = cr.fetchone()
    return row[0] if row else None


def state(label, cr):
    out('  %-18s строк: %-4s  %s: %-4s  %s: %-4s  FK RESTRICT: %s'
        % (label,
           one('SELECT count(*) FROM %s' % TABLE),
           OLD_COL, one('SELECT count(*) FROM %s WHERE %s IS NOT NULL'
                        % (TABLE, OLD_COL)) if column(cr, OLD_COL) else '—',
           NEW_COL, one('SELECT count(*) FROM %s WHERE %s IS NOT NULL'
                        % (TABLE, NEW_COL)) if column(cr, NEW_COL) else '—',
           one("SELECT count(*) FROM pg_constraint WHERE conname = 'op_parent_partner_id_fkey'"
               " AND contype = 'f'")))


cr = env.cr

out('=== ДО ===')
old_type, new_type = column(cr, OLD_COL), column(cr, NEW_COL)
out('  колонка %-10s %s | колонка %-10s %s' % (OLD_COL, old_type,
                                              NEW_COL, new_type))
state('текущее', cr)

if new_type and not old_type:
    out('УЖЕ МИГРИРОВАНО: колонка name отсутствует, partner_id есть. '
        'Ничего не меняю, нужен только -u openeducat_parent.')
    env.cr.commit()
    raise SystemExit(0)
if old_type != 'integer':
    out('ОСТАНОВ: нет колонки name (integer) — база в неожиданном '
        'состоянии, ручная проверка перед миграцией.')
    raise SystemExit(1)

broken = one("""
    SELECT count(*) FROM op_parent p
     LEFT JOIN res_partner r ON r.id = p.name
     WHERE r.id IS NULL
""")
if broken:
    out('ОСТАНОВ: %s записей op.parent ссылаются на несуществующий контакт — '
        'сначала починить данные, иначе RENAME закрепит битые ссылки.' % broken)
    raise SystemExit(1)

# 1. устаревший constraint (уникальность будет объявлена на partner_id)
cr.execute('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %s' % (TABLE, OLD_CONSTRAINT))
out('  1. constraint %s снят' % OLD_CONSTRAINT)

# 2. переименование колонки и FK
cr.execute('ALTER TABLE %s RENAME COLUMN %s TO %s' % (TABLE, OLD_COL, NEW_COL))
out('  2. колонка %s -> %s' % (OLD_COL, NEW_COL))
if one("SELECT 1 FROM pg_constraint WHERE conname = %s AND conrelid = %s::regclass",
       (OLD_FK, TABLE)):
    cr.execute('ALTER TABLE %s RENAME CONSTRAINT %s TO %s'
               % (TABLE, OLD_FK, NEW_FK))
    out('     FK %s -> %s' % (OLD_FK, NEW_FK))

# 3. метаданные поля: Odoo сопоставляет поля по (model, name), а не по xmlid
cr.execute("""
    UPDATE ir_model_fields SET name = %s
     WHERE model = %s AND name = %s
""", (NEW_COL, MODEL, OLD_COL))
out('  3. ir_model_fields: %s.%s -> %s (строк обновлено: %s)'
    % (MODEL, OLD_COL, NEW_COL, cr.rowcount))
cr.execute("""
    SELECT count(*) FROM ir_model_fields WHERE model = %s AND name = %s
""", (MODEL, NEW_COL))
if cr.fetchone()[0] != 1:
    out('ОСТАНОВ: ожидалась ровно одна строка ir_model_fields для '
        '%s.%s — откат (RENAME обратно).' % (MODEL, NEW_COL))
    raise SystemExit(1)

# 4. xmlid поля, чтобы -u обновил ту же запись, а не создал дубль
IMD = env['ir.model.data'].sudo()
xid = IMD.search([('module', '=', MODULE), ('name', '=', OLD_XMLID)], limit=1)
if xid:
    clash = IMD.search([('module', '=', MODULE), ('name', '=', NEW_XMLID)],
                       limit=1)
    if clash:
        out('ОСТАНОВ: xmlid %s.%s уже существует (res_id=%s) — разбирать '
            'вручную.' % (MODULE, NEW_XMLID, clash.res_id))
        raise SystemExit(1)
    xid.write({'name': NEW_XMLID})
    out('  4. xmlid %s.%s -> %s (ir_model.fields res_id=%s)'
        % (MODULE, OLD_XMLID, NEW_XMLID, xid.res_id))
else:
    out('  4. xmlid %s.%s не найден — пропускаю (уже был переименован?)'
        % (MODULE, OLD_XMLID))

env.cr.commit()

out('=== ПОСЛЕ ===')
state('после миграции', env.cr)
env.cr.execute('SELECT count(*) FROM (SELECT partner_id FROM op_parent'
               ' GROUP BY partner_id HAVING count(*) > 1) d')
out('  дублей partner_id: %s' % env.cr.fetchone()[0])
env.cr.execute('SELECT id, partner_id FROM op_parent ORDER BY id LIMIT 3')
out('  пример id|partner_id: %s' % env.cr.fetchall())
out('ГОТОВО. Дальше — -u openeducat_parent (создаст колонку name (char), '
    'пересчитает related, вернёт constraint unique(partner_id)).')
