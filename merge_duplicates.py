#!/usr/bin/env python3
"""
Скрипт объединения дубликатов op.media + перенос полей в op.media_unit.

Что делает:
  1. Добавляет isbn/edition/x_issue_year в op_media_unit, переносит данные из op_media
  2. Находит дубликаты op.media (по имени + авторам)
  3. Объединяет: переносит связи, движения, вложения на keep_id
  4. Удаляет дубликаты из op_media
  5. Перенумеровывает экземпляры
  6. Удаляет isbn/edition/x_issue_year из op_media (данные уже в op_media_unit)

Запуск:
    cd ~/odoo-dev && docker compose exec odoo python3 /mnt/extra-addons/merge_duplicates.py [--dry-run]
"""

import sys
import json
import psycopg2
from datetime import datetime

# ============================================================
# ПРЕДПОЧТИТЕЛЬНЫЕ ОБЛОЖКИ (ISBN → оставить обложку этой записи)
# ============================================================
PREFERRED_ISBN = {
    '9785090874403', '9785090361040', '9785090541527', '9785090532952',
    '9785090378536', '9785090360678', '9785090347099', '9785090465663',
    '9785090875691', '9785090779159', '9785090717298', '9785090190916',
    '9785090577649', '9785090774321', '9785360062936', '9785090797351',
    '9785091108101', '9785090802604', '9785091121629', '9785091201611',
    '9785091201628', '9785090739375', '9785090284868', '9785091025507',
    '9785090203746', '9785090358705', '9785090237222', '9785090318266',
    '9785090308540', '9785090211369', '9785358114494', '9785358154001',
    '9785090703994', '9785090321723', '9785090878364', '9785090464635',
    '9875090781367', '9785090441919', '9785090846264', '9785090779364',
    '9785090358774', '9785090550048', '9785090358514', '9785090358538',
    '9785090550093', '9785090465601', '9785090550482', '9785090302944',
    '9785090227308', '9785090251495', '9785346045748', '9785346045816',
    '9785346045816-1', '9785091025330', '9785091025347', '9785090739269',
    '9785090465205', '9785090233316', '9785090463065', '9785533017916',
    '9785090344623', '9785090344616', '9785090202879', '9785090360296',
    '9785090345651', '9785090346030', '9785090245425', '9785937621580',
    '9785090282253', '9785710771570', '9785090786317', '9785358165281',
    '9785358197206', '9785358177833', '9785090720885', '9785090742429',
    '9785358194199', '9785090779500',
}

DB_CONFIG = {
    'host': 'db', 'port': 5432, 'dbname': 'test4',
    'user': 'odoo', 'password': 'odoo',
}

BKP_PREFIX = "_bkp_merge_"
BKP_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

TABLES_TO_BACKUP = [
    "op_media", "op_media_unit", "op_media_movement",
    "op_course_op_media_rel", "op_media_op_subject_rel",
    "op_author_op_media_rel", "op_media_op_publisher_rel", "op_media_op_tag_rel",
]


def connect():
    return psycopg2.connect(**DB_CONFIG)


def create_backups(cr):
    ts = BKP_PREFIX + BKP_TIMESTAMP
    for table in TABLES_TO_BACKUP:
        bkp_name = f"{BKP_PREFIX}{table}_{ts}"
        print(f"  BKP: {table} -> {bkp_name}")
        cr.execute(f"DROP TABLE IF EXISTS {bkp_name}")
        cr.execute(f"CREATE TABLE {bkp_name} AS SELECT * FROM {table}")
    bkp_name = f"{BKP_PREFIX}ir_attachment_{ts}"
    print(f"  BKP: ir_attachment (op.media) -> {bkp_name}")
    cr.execute(f"DROP TABLE IF EXISTS {bkp_name}")
    cr.execute(f"CREATE TABLE {bkp_name} AS SELECT * FROM ir_attachment WHERE res_model = 'op.media'")
    print(f"\nBKP таблицы созданы с суффиксом {ts}")
    return ts


def add_columns_to_media_unit(cr):
    """Добавить isbn/edition/x_issue_year в op_media_unit, перенести данные из op_media."""
    print("  Добавление столбцов в op_media_unit...")
    cr.execute("ALTER TABLE op_media_unit ADD COLUMN IF NOT EXISTS isbn varchar")
    cr.execute("ALTER TABLE op_media_unit ADD COLUMN IF NOT EXISTS edition varchar")
    cr.execute("ALTER TABLE op_media_unit ADD COLUMN IF NOT EXISTS x_issue_year varchar")

    print("  Перенос данных из op_media в op_media_unit...")
    cr.execute("""
        UPDATE op_media_unit mu
        SET isbn = m.isbn,
            edition = COALESCE(mu.edition, m.edition),
            x_issue_year = COALESCE(mu.x_issue_year, m.x_issue_year)
        FROM op_media m
        WHERE mu.media_id = m.id
          AND (mu.isbn IS NULL OR mu.edition IS NULL OR mu.x_issue_year IS NULL)
    """)
    print(f"    Обновлено {cr.rowcount} строк")

    # Зарегистрировать поля в ir_model_fields
    print("  Регистрация полей в ir_model_fields...")
    cr.execute("SELECT id FROM ir_model WHERE model = 'op.media.unit'")
    row = cr.fetchone()
    if not row:
        print("  ОШИБКА: модель op.media.unit не найдена")
        return
    model_id = row[0]

    for fname, fdesc in [('isbn', 'ISBN Code'), ('edition', 'Edition'), ('x_issue_year', 'Issue Year')]:
        cr.execute("""
            INSERT INTO ir_model_fields (model_id, model, name, field_description, ttype, state)
            VALUES (%s, 'op.media.unit', %s, %s::jsonb, 'char', 'base')
            ON CONFLICT DO NOTHING
        """, (model_id, fname, json.dumps({"en_US": fdesc})))
    print("    Поля зарегистрированы")


def get_duplicate_groups(cr):
    """Группировка дубликатов по name + набор авторов."""
    cr.execute("""
        SELECT regexp_replace(m.name, '\\s*-\\s*', '-', 'g') as norm_name,
            ARRAY_AGG(m.id ORDER BY m.id) as all_ids,
            COUNT(*) as cnt
        FROM op_media m
        LEFT JOIN op_author_op_media_rel rel ON rel.op_media_id = m.id
        LEFT JOIN op_author a ON a.id = rel.op_author_id
        GROUP BY regexp_replace(m.name, '\\s*-\\s*', '-', 'g')
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    """)
    name_rows = list(cr.fetchall())

    # Собрать авторов для каждой книги
    cr.execute("""
        SELECT m.id, ARRAY_AGG(a.name ORDER BY a.name) as authors
        FROM op_media m
        LEFT JOIN op_author_op_media_rel rel ON rel.op_media_id = m.id
        LEFT JOIN op_author a ON a.id = rel.op_author_id
        GROUP BY m.id
    """)
    media_authors = {}
    for mid, authors in cr.fetchall():
        media_authors[mid] = tuple(authors) if authors and authors[0] else ()

    groups = []
    for row in name_rows:
        name, all_ids, cnt = row

        # Разделить на подгруппы по авторам
        by_authors = {}
        for mid in all_ids:
            key = media_authors.get(mid, ())
            by_authors.setdefault(key, []).append(mid)

        for author_key, sub_ids in by_authors.items():
            if len(sub_ids) < 2:
                continue

            # Выбрать keep_id: приоритет — запись с предпочтительным ISBN
            keep_id = None
            for mid in sub_ids:
                cr.execute("SELECT isbn FROM op_media WHERE id = %s", (mid,))
                isbn = cr.fetchone()[0]
                if isbn and isbn in PREFERRED_ISBN:
                    keep_id = mid
                    break
            if keep_id is None:
                keep_id = sub_ids[0]

            delete_ids = [i for i in sub_ids if i != keep_id]
            cr.execute("SELECT name FROM op_media WHERE id = %s", (keep_id,))
            real_name = cr.fetchone()[0]
            groups.append({
                'name': real_name,
                'keep_id': keep_id,
                'all_ids': sub_ids,
                'delete_ids': delete_ids,
                'count': len(sub_ids),
            })

    preferred_count = sum(1 for g in groups if g['keep_id'] != g['all_ids'][0])
    if preferred_count:
        print(f"  [cover] {preferred_count} групп: keep_id выбран по предпочтительному ISBN")

    return groups


def collect_relations(cr, groups):
    all_dup_ids = []
    for g in groups:
        all_dup_ids.extend(g['all_ids'])
    old_to_keep = {oid: g['keep_id'] for g in groups for oid in g['all_ids']}
    keep_ids_set = set(g['keep_id'] for g in groups)
    all_ids_for_rel = list(set(all_dup_ids) | keep_ids_set)
    relations = {}
    for rel_type, table, id_col in [
        ('course', 'op_course_op_media_rel', 'op_course_id'),
        ('subject', 'op_media_op_subject_rel', 'op_subject_id'),
        ('author', 'op_author_op_media_rel', 'op_author_id'),
        ('publisher', 'op_media_op_publisher_rel', 'op_publisher_id'),
        ('tag', 'op_media_op_tag_rel', 'op_tag_id'),
    ]:
        cr.execute(f"SELECT op_media_id, {id_col} FROM {table} WHERE op_media_id = ANY(%s)", (all_ids_for_rel,))
        for old_id, val in cr.fetchall():
            target_id = old_to_keep.get(old_id, old_id)
            relations.setdefault((rel_type, target_id), set()).add(val)
    return relations, old_to_keep


def merge_relations(cr, relations, keep_ids):
    rel_tables = {
        'course': ('op_course_op_media_rel', 'op_course_id'),
        'subject': ('op_media_op_subject_rel', 'op_subject_id'),
        'author': ('op_author_op_media_rel', 'op_author_id'),
        'publisher': ('op_media_op_publisher_rel', 'op_publisher_id'),
        'tag': ('op_media_op_tag_rel', 'op_tag_id'),
    }
    for rel_type, (table, id_col) in rel_tables.items():
        cr.execute(f"DELETE FROM {table} WHERE op_media_id = ANY(%s)", (list(keep_ids),))
    for (rel_type, keep_id), related_ids in relations.items():
        table, id_col = rel_tables[rel_type]
        for rid in related_ids:
            cr.execute(f"INSERT INTO {table} (op_media_id, {id_col}) VALUES (%s, %s) ON CONFLICT DO NOTHING", (keep_id, rid))


def update_media_units(cr, old_to_keep):
    updated = 0
    for old_id, new_id in old_to_keep.items():
        if old_id != new_id:
            cr.execute("UPDATE op_media_unit SET media_id = %s WHERE media_id = %s", (new_id, old_id))
            updated += cr.rowcount
    return updated


def update_media_movements(cr, old_to_keep):
    updated = 0
    for old_id, new_id in old_to_keep.items():
        if old_id != new_id:
            cr.execute("UPDATE op_media_movement SET media_id = %s WHERE media_id = %s", (new_id, old_id))
            updated += cr.rowcount
    return updated


def update_ir_attachments(cr, old_to_keep):
    dup_ids = [old_id for old_id, new_id in old_to_keep.items() if old_id != new_id]
    if not dup_ids:
        return 0
    cr.execute("DELETE FROM ir_attachment WHERE res_model = 'op.media' AND res_id = ANY(%s)", (dup_ids,))
    return cr.rowcount


def renumber_units(cr, groups):
    total = 0
    for group in groups:
        cr.execute("""
            SELECT mu.id, m.name FROM op_media_unit mu
            JOIN op_media m ON m.id = mu.media_id
            WHERE mu.media_id = %s ORDER BY mu.id
        """, (group['keep_id'],))
        for idx, (unit_id, book_name) in enumerate(cr.fetchall(), 1):
            cr.execute("UPDATE op_media_unit SET name = %s WHERE id = %s",
                      (f"{book_name} - {idx:02d}", unit_id))
            total += 1
    return total


def delete_duplicates(cr, groups):
    total = 0
    for group in groups:
        cr.execute("DELETE FROM op_media WHERE id = ANY(%s)", (group['delete_ids'],))
        total += cr.rowcount
    return total


# ============================================================
# MAIN
# ============================================================

DRY_RUN = '--dry-run' in sys.argv

print("=" * 70)
print("МИГРАЦИЯ op.media: перенос полей + объединение дубликатов")
print(f"Время: {BKP_TIMESTAMP}")
if DRY_RUN:
    print("*** DRY RUN — изменения НЕ применяются ***")
print("=" * 70)

print(f"\nПодключение к БД {DB_CONFIG['dbname']}...")
conn = connect()
conn.autocommit = False
cr = conn.cursor()
print("OK")

try:
    # 0. Добавить столбцы в op_media_unit
    print("\n[0] Добавление столбцов в op_media_unit...")
    add_columns_to_media_unit(cr)

    # 1. Анализ дубликатов
    print("\n[1] Анализ дубликатов...")
    groups = get_duplicate_groups(cr)
    total_dups = sum(g['count'] for g in groups)
    total_to_delete = sum(len(g['delete_ids']) for g in groups)
    all_dup_ids = []
    for g in groups:
        all_dup_ids.extend(g['all_ids'])
    cr.execute("SELECT COUNT(*) FROM op_media_unit WHERE media_id = ANY(%s)", (all_dup_ids,))
    units_count = cr.fetchone()[0]
    print(f"    Групп: {len(groups)}")
    print(f"    Книг в группах: {total_dups}")
    print(f"    К удалению: {total_to_delete}")
    print(f"    Экземпляров затронуто: {units_count}")

    # 2. BKP
    print("\n[2] Создание BKP таблиц...")
    ts = create_backups(cr)

    # 3. Сбор связей
    print("\n[3] Сбор связей...")
    relations, old_to_keep = collect_relations(cr, groups)
    print(f"    Собрано {len(relations)} связей")

    # 4. Обновление связей
    print("\n[4] Обновление связей...")
    merge_relations(cr, relations, set(g['keep_id'] for g in groups))
    print("    Связи обновлены")

    # 5. Обновление media_unit
    print("\n[5] Обновление media_unit.media_id...")
    units_updated = update_media_units(cr, old_to_keep)
    print(f"    Обновлено {units_updated} экземпляров")

    # 6. Обновление media_movement
    print("\n[6] Обновление media_movement.media_id...")
    movements_updated = update_media_movements(cr, old_to_keep)
    print(f"    Обновлено {movements_updated} движений")

    # 7. Удаление вложений дубликатов
    print("\n[7] Удаление вложений дубликатов...")
    attachments_deleted = update_ir_attachments(cr, old_to_keep)
    print(f"    Удалено {attachments_deleted} вложений дубликатов")

    # 8. Удаление дубликатов
    print("\n[8] Удаление дубликатов...")
    deleted = delete_duplicates(cr, groups)
    print(f"    Удалено {deleted} дубликатов")

    # 9. Перенумерация
    print("\n[9] Перенумерация экземпляров...")
    renamed = renumber_units(cr, groups)
    print(f"    Переименовано {renamed} экземпляров")

    # 10. Удалить старые столбцы из op_media
    print("\n[10] Удаление старых столбцов из op_media...")
    cr.execute("ALTER TABLE op_media DROP COLUMN IF EXISTS isbn")
    cr.execute("ALTER TABLE op_media DROP COLUMN IF EXISTS edition")
    cr.execute("ALTER TABLE op_media DROP COLUMN IF EXISTS x_issue_year")
    print("    Столбцы isbn/edition/x_issue_year удалены из op_media")

    # Commit или rollback
    if DRY_RUN:
        conn.rollback()
        print("\n" + "=" * 70)
        print("DRY RUN — откат (rollback). Изменения НЕ сохранены.")
    else:
        conn.commit()
        print("\n" + "=" * 70)
        print("Изменения сохранены (commit).")

    print("=" * 70)
    print("ИТОГО:")
    print(f"  Групп: {len(groups)}")
    print(f"  Книг в группах: {total_dups}")
    print(f"  К удалению: {deleted}")
    print(f"  Экземпляров переименовано: {renamed}")
    print(f"  Движений обновлено: {movements_updated}")
    print(f"  Вложений дубликатов удалено: {attachments_deleted}")
    if not DRY_RUN:
        print(f"  BKP: _bkp_merge_*_{ts}")
    print("=" * 70)

except Exception as e:
    conn.rollback()
    print(f"\nОШИБКА: {e}")
    print("Откат (rollback) выполнен.")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    cr.close()
    conn.close()
