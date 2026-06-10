#!/usr/bin/env python3
"""
Скрипт объединения дубликатов op.media — Вариант 1Б.
Переносит isbn/edition/x_issue_year на op.media.unit,
затем объединяет дубликаты op.media в одну книгу.

Запуск:
    cd ~/odoo-dev && docker compose exec odoo python3 /mnt/extra-addons/merge_duplicates_v2.py

Требования:
    - Odoo должен быть запущен
    - psycopg2 доступен в контейнере
    - Полный бэкап базы уже сделан
"""

import sys
import psycopg2
from datetime import datetime

# ============================================================
# ПРЕДПОЧТИТЕЛЬНЫЕ ОБЛОЖКИ (ISBN → keep_id для группы)
# При объединении дубликатов keep_id = запись с этим ISBN.
# Обложка (ir_attachment) дубликатов удаляется.
# ============================================================
PREFERRED_ISBN = {
    '9785090874403',  # Spotlight 10
    '9785090361040',  # Spotlight 11
    '9785090541527',  # Spotlight 5
    '9785090532952',  # Spotlight 6
    '9785090378536',  # Spotlight 7
    '9785090360678',  # Spotlight 8
    '9785090347099',  # Spotlight 9 класс
    '9785090465663',  # Алгебра 7 класс
    '9785090875691',  # Алгебра 8
    '9785090779159',  # Алгебра 9 класс
    '9785090717298',  # Алгебра и начала математического анализа 10-11
    '9785090190916',  # Биология 10-11 класс
    '9785090577649',  # Биология 10 класс
    '9785090774321',  # Биология 11 класс
    '9785360062936',  # Биология 5 класс
    '9785090797351',  # Биология 6 класс
    '9785091108101',  # Биология 7 класс
    '9785090802604',  # Биология 8 класс (Драгмилов/Маш)
    '9785091121629',  # Биология 8 класс (Пасечник/Суматохин)
    '9785091201611',  # Вероятность и статистика Часть 1
    '9785091201628',  # Вероятность и статистика Часть 2
    '9785090739375',  # Всеобщая история 7 класс
    '9785090284868',  # География 10-11 класс
    '9785091025507',  # География 5-6 класс
    '9785090203746',  # География 6 класс
    '9785090358705',  # География 7 класс
    '9785090237222',  # География 8 класс
    '9785090318266',  # География 9 класс
    '9785090308540',  # Геометрия 10-11 класс
    '9785090211369',  # Геометрия 7 8 9 класс
    '9785358114494',  # Искусство 6 класс
    '9785358154001',  # Искусство 6 класс Рабочая тетрадь
    '9785090703994',  # История 10 класс
    '9785090321723',  # История 5 класс
    '9785090878364',  # История 6 класс
    '9785090464635',  # История 8 класс
    '9875090781367',  # История 9 класс (Всеобщая история)
    '9785090441919',  # История России 6 класс 1 часть
    '9785090846264',  # История России 8 класс Часть 1
    '9785090779364',  # История России 9 Часть 1
    '9785090358774',  # Литература 5 класс Часть 1
    '9785090550048',  # Литература 5 класс Часть 2
    '9785090358514',  # Литература 6 класс 1 часть
    '9785090358538',  # Литература 6 класс Часть 2
    '9785090550093',  # Литература 7 класс Часть 1
    '9785090465601',  # Литература 8 класс Часть 1
    '9785090550482',  # Литература 8 класс Часть 2
    '9785090302944',  # Литература 9 класс
    '9785090227308',  # Литература 9 класс часть 1
    '9785090251495',  # Литература 9 класс Часть 2
    '9785346045748',  # Математика 5 класс Часть 1
    '9785346045816',  # Математика 5 класс Часть 2
    '9785346045816-1',  # Математика 5 класс Часть 2 (суффикс)
    '9785091025330',  # Математика 6 класс 1 часть
    '9785091025347',  # Математика 6 класс 2 часть
    '9785090739269',  # Обществознание 10 класс
    '9785090465205',  # Обществознание 9 класс
    '9785090233316',  # Русский язык 10-11 (Греков/Крючков/Чешко)
    '9785090463065',  # Русский язык 10-11 (Власенков/Рыбченкова)
    '9785533017916',  # Русский язык 10-11 (Гольцова/Шамшин/Мищерина)
    '9785090344623',  # Русский язык 5 класс Часть 1
    '9785090344616',  # Русский язык 5 класс Часть 2
    '9785090202879',  # Русский язык 6 класс Часть 1
    '9785090360296',  # Русский язык 6 класс Часть 2
    '9785090345651',  # Русский язык 7 класс
    '9785090346030',  # Русский язык 8 класс
    '9785090245425',  # Русский язык 9 класс
    '9785937621580',  # Словарь ключевых понятий христианского богословия
    '9785090282253',  # Физика 10 (Мякишев/Буховцев/Сотский)
    '9785710771570',  # Физика 10 (Касьянов)
    '9785090786317',  # Физика 11 Классический курс
    '9785358165281',  # Физика 7 класс
    '9785358197206',  # Физика 8 класс
    '9785358177833',  # Физика 9 класс
    '9785090720885',  # Химия 10
    '9785090742429',  # Химия 11
    '9785358194199',  # Химия 8 класс
    '9785090779500',  # Химия 9 класс
}

# ============================================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К БД
# ============================================================
DB_CONFIG = {
    'host': 'db',
    'port': 5432,
    'dbname': 'test4',
    'user': 'odoo',
    'password': 'odoo',
}

BKP_PREFIX = "_bkp_merge_v2_"
BKP_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

TABLES_TO_BACKUP = [
    "op_media",
    "op_media_unit",
    "op_media_movement",
    "op_course_op_media_rel",
    "op_media_op_subject_rel",
    "op_author_op_media_rel",
    "op_media_op_publisher_rel",
    "op_media_op_tag_rel",
]


def connect():
    return psycopg2.connect(**DB_CONFIG)


def create_backups(cr):
    """Шаг 0: BKP таблиц."""
    ts = BKP_TIMESTAMP
    for table in TABLES_TO_BACKUP:
        bkp_name = f"{BKP_PREFIX}{table}_{ts}"
        print(f"  BKP: {table} -> {bkp_name}")
        cr.execute(f"DROP TABLE IF EXISTS {bkp_name}")
        cr.execute(f"CREATE TABLE {bkp_name} AS SELECT * FROM {table}")
    # ir_attachment — только op.media
    bkp_name = f"{BKP_PREFIX}ir_attachment_{ts}"
    print(f"  BKP: ir_attachment (op.media) -> {bkp_name}")
    cr.execute(f"DROP TABLE IF EXISTS {bkp_name}")
    cr.execute(
        f"CREATE TABLE {bkp_name} AS SELECT * FROM ir_attachment "
        f"WHERE res_model = 'op.media'"
    )
    print(f"\n  BKP таблицы созданы с суффиксом {ts}")
    return ts


def add_unit_fields(cr):
    """Шаг 1: Добавить isbn, edition, x_issue_year на op_media_unit."""
    print("  Добавление полей на op_media_unit...")
    cr.execute("""
        ALTER TABLE op_media_unit
            ADD COLUMN IF NOT EXISTS isbn varchar,
            ADD COLUMN IF NOT EXISTS edition varchar,
            ADD COLUMN IF NOT EXISTS x_issue_year varchar
    """)
    # Проверить что поля добавлены
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'op_media_unit'
        AND column_name IN ('isbn', 'edition', 'x_issue_year')
        ORDER BY column_name
    """)
    cols = [r[0] for r in cr.fetchall()]
    print(f"  Поля на op_media_unit: {cols}")
    if len(cols) != 3:
        raise Exception(f"Не все поля добавлены: {cols}")
    return True


def migrate_media_fields_to_units(cr):
    """Шаг 2: Копировать isbn, edition, x_issue_year из op.media в op.media.unit."""
    cr.execute("""
        UPDATE op_media_unit mu
        SET isbn = m.isbn,
            edition = m.edition,
            x_issue_year = m.x_issue_year
        FROM op_media m
        WHERE mu.media_id = m.id
          AND (m.isbn IS NOT NULL OR m.edition IS NOT NULL OR m.x_issue_year IS NOT NULL)
    """)
    updated = cr.rowcount
    print(f"  Обновлено {updated} экземпляров (isbn/edition/year скопированы)")
    return updated


def get_duplicate_groups(cr):
    """Шаг 3: Найти группы дубликатов по name."""
    cr.execute("""
        SELECT m.name,
               ARRAY_AGG(m.id ORDER BY m.id) as all_ids,
               COUNT(*) as cnt
        FROM op_media m
        GROUP BY m.name
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    """)

    groups = []
    for name, all_ids, cnt in cr.fetchall():
        # Определить keep_id: приоритет → PREFERRED_ISBN → макс. units → мин. id
        keep_id = None

        # Ищем по предпочтительному ISBN
        for mid in all_ids:
            cr.execute("SELECT isbn FROM op_media WHERE id = %s", (mid,))
            isbn = cr.fetchone()[0]
            if isbn and isbn in PREFERRED_ISBN:
                keep_id = mid
                break

        # Если не нашли — берём с макс. количеством units
        if keep_id is None:
            cr.execute("""
                SELECT m.id, COUNT(mu.id) as unit_cnt
                FROM op_media m
                LEFT JOIN op_media_unit mu ON mu.media_id = m.id
                WHERE m.id = ANY(%s)
                GROUP BY m.id
                ORDER BY unit_cnt DESC, m.id ASC
                LIMIT 1
            """, (all_ids,))
            keep_id = cr.fetchone()[0]

        delete_ids = [i for i in all_ids if i != keep_id]
        groups.append({
            'name': name,
            'keep_id': keep_id,
            'all_ids': all_ids,
            'delete_ids': delete_ids,
            'count': len(all_ids),
        })

    preferred_count = sum(1 for g in groups if g['keep_id'] != g['all_ids'][0])
    if preferred_count:
        print(f"  [cover] {preferred_count} групп: keep_id выбран по предпочтительному ISBN")

    return groups


def collect_m2m_relations(cr, groups):
    """Шаг 4: Собрать все m2m связи дубликатов."""
    all_dup_ids = []
    for g in groups:
        all_dup_ids.extend(g['all_ids'])
    old_to_keep = {oid: g['keep_id'] for g in groups for oid in g['all_ids']}

    relations = {}
    for rel_type, table, id_col in [
        ('course', 'op_course_op_media_rel', 'op_course_id'),
        ('subject', 'op_media_op_subject_rel', 'op_subject_id'),
        ('author', 'op_author_op_media_rel', 'op_author_id'),
        ('publisher', 'op_media_op_publisher_rel', 'op_publisher_id'),
        ('tag', 'op_media_op_tag_rel', 'op_tag_id'),
    ]:
        cr.execute(
            f"SELECT op_media_id, {id_col} FROM {table} "
            f"WHERE op_media_id = ANY(%s)", (all_dup_ids,)
        )
        for old_id, val in cr.fetchall():
            relations.setdefault((rel_type, old_to_keep[old_id]), set()).add(val)

    return relations, old_to_keep


def merge_m2m_relations(cr, relations, keep_ids):
    """Шаг 5: Перенести m2m связи на keep_id."""
    rel_tables = {
        'course': ('op_course_op_media_rel', 'op_course_id'),
        'subject': ('op_media_op_subject_rel', 'op_subject_id'),
        'author': ('op_author_op_media_rel', 'op_author_id'),
        'publisher': ('op_media_op_publisher_rel', 'op_publisher_id'),
        'tag': ('op_media_op_tag_rel', 'op_tag_id'),
    }
    # Удалить старые связи на keep_id
    for rel_type, (table, id_col) in rel_tables.items():
        cr.execute(f"DELETE FROM {table} WHERE op_media_id = ANY(%s)", (list(keep_ids),))
    # Вставить собранные уникальные связи
    for (rel_type, keep_id), related_ids in relations.items():
        table, id_col = rel_tables[rel_type]
        for rid in related_ids:
            cr.execute(
                f"INSERT INTO {table} (op_media_id, {id_col}) VALUES (%s, %s) "
                f"ON CONFLICT DO NOTHING",
                (keep_id, rid)
            )


def update_units_media_id(cr, old_to_keep):
    """Шаг 6: Перепривязать units дубликатов на keep_id."""
    updated = 0
    for old_id, new_id in old_to_keep.items():
        if old_id != new_id:
            cr.execute(
                "UPDATE op_media_unit SET media_id = %s WHERE media_id = %s",
                (new_id, old_id)
            )
            updated += cr.rowcount
    return updated


def update_movements(cr, old_to_keep):
    """Шаг 7: Перепривязать movements дубликатов на keep_id."""
    updated = 0
    for old_id, new_id in old_to_keep.items():
        if old_id != new_id:
            cr.execute(
                "UPDATE op_media_movement SET media_id = %s WHERE media_id = %s",
                (new_id, old_id)
            )
            updated += cr.rowcount
    return updated


def delete_duplicate_attachments(cr, old_to_keep):
    """Шаг 8: Удалить вложения (обложки) дубликатов."""
    dup_ids = [old_id for old_id, new_id in old_to_keep.items() if old_id != new_id]
    if not dup_ids:
        return 0
    cr.execute(
        "DELETE FROM ir_attachment WHERE res_model = 'op.media' AND res_id = ANY(%s)",
        (dup_ids,)
    )
    return cr.rowcount


def delete_duplicates(cr, groups):
    """Шаг 9: Удалить дубликаты op.media."""
    total = 0
    for group in groups:
        cr.execute("DELETE FROM op_media WHERE id = ANY(%s)", (group['delete_ids'],))
        total += cr.rowcount
    return total


def remove_unique_constraints(cr):
    """Шаг 10: Убрать UNIQUE constraints на op_media.isbn."""
    print("  Удаление UNIQUE constraints на op_media...")
    cr.execute("""
        ALTER TABLE op_media
            DROP CONSTRAINT IF EXISTS op_media_isbn_uniq
    """)
    cr.execute("""
        ALTER TABLE op_media
            DROP CONSTRAINT IF EXISTS op_media_unique_name_isbn
    """)
    # Проверить
    cr.execute("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'op_media' AND constraint_type = 'UNIQUE'
    """)
    remaining = cr.fetchall()
    if remaining:
        print(f"  ⚠ Остались constraints: {[r[0] for r in remaining]}")
    else:
        print("  UNIQUE constraints удалены")


def renumber_units(cr, groups):
    """Шаг 11: Перенумеровать units после слияния."""
    total = 0
    for group in groups:
        cr.execute("""
            SELECT mu.id, m.name
            FROM op_media_unit mu
            JOIN op_media m ON m.id = mu.media_id
            WHERE mu.media_id = %s
            ORDER BY mu.id
        """, (group['keep_id'],))
        for idx, (unit_id, book_name) in enumerate(cr.fetchall(), 1):
            cr.execute(
                "UPDATE op_media_unit SET name = %s WHERE id = %s",
                (f"{book_name} - {idx:02d}", unit_id)
            )
            total += 1
    return total


def validate(cr):
    """Шаг 12: Валидация результата."""
    warnings = []

    # 1. Нет дубликатов по name
    cr.execute("""
        SELECT name, COUNT(*) FROM op_media GROUP BY name HAVING COUNT(*) > 1
    """)
    dups = cr.fetchall()
    if dups:
        warnings.append(f"⚠ Олись дубликаты по name: {len(dups)} групп")

    # 2. Все units имеют media_id на существующую книгу
    cr.execute("""
        SELECT COUNT(*) FROM op_media_unit mu
        WHERE NOT EXISTS (SELECT 1 FROM op_media m WHERE m.id = mu.media_id)
    """)
    orphans = cr.fetchone()[0]
    if orphans:
        warnings.append(f"⚠ Orphan units (без книги): {orphans}")

    # 3. Все movements имеют media_id на существующую книгу
    cr.execute("""
        SELECT COUNT(*) FROM op_media_movement mm
        WHERE NOT EXISTS (SELECT 1 FROM op_media m WHERE m.id = mm.media_id)
    """)
    orphan_moves = cr.fetchone()[0]
    if orphan_moves:
        warnings.append(f"⚠ Orphan movements: {orphan_moves}")

    # 4. Нет units без isbn (у дубликатов был isbn)
    cr.execute("SELECT COUNT(*) FROM op_media_unit WHERE isbn IS NULL OR isbn = ''")
    no_isbn = cr.fetchone()[0]
    if no_isbn:
        print(f"  ℹ Units без ISBN: {no_isbn} (норма для книг без ISBN)")

    # 5. Статистика
    cr.execute("SELECT COUNT(*) FROM op_media")
    media_count = cr.fetchone()[0]
    cr.execute("SELECT COUNT(*) FROM op_media_unit")
    unit_count = cr.fetchone()[0]
    cr.execute("SELECT COUNT(*) FROM op_media_movement")
    move_count = cr.fetchone()[0]

    print(f"\n  Статистика после миграции:")
    print(f"    Книг (op.media): {media_count}")
    print(f"    Экземпляров (op.media.unit): {unit_count}")
    print(f"    Движений (op.media.movement): {move_count}")

    if warnings:
        print(f"\n  ⚠ ПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print(f"    {w}")
    else:
        print(f"\n  ✅ Валидация пройдена, предупреждений нет")

    return len(warnings) == 0


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("ОБЪЕДИНЕНИЕ ДУБЛИКАТОВ op.media v2 (Вариант 1Б)")
print(f"Время: {BKP_TIMESTAMP}")
print("=" * 70)

print(f"\nПодключение к БД {DB_CONFIG['dbname']}...")
conn = connect()
conn.autocommit = False
cr = conn.cursor()
print("OK")

try:
    # 0. Анализ
    print("\n[0] Анализ дубликатов...")
    cr.execute("""
        SELECT COUNT(*), COUNT(DISTINCT name) FROM op_media
    """)
    total_media, unique_names = cr.fetchone()
    cr.execute("""
        SELECT COUNT(*) FROM (
            SELECT name FROM op_media GROUP BY name HAVING COUNT(*) > 1
        ) t
    """)
    dup_groups = cr.fetchone()[0]
    print(f"    Всего книг: {total_media}")
    print(f"    Уникальных названий: {unique_names}")
    print(f"    Групп дубликатов: {dup_groups}")

    # 1. BKP
    print("\n[1] Создание BKP таблиц...")
    ts = create_backups(cr)

    # 2. Добавить поля на op_media_unit
    print("\n[2] Добавление полей на op_media_unit...")
    add_unit_fields(cr)

    # 3. Мигрировать isbn/edition/year → op_media_unit
    print("\n[3] Миграция isbn/edition/year в op_media_unit...")
    units_migrated = migrate_media_fields_to_units(cr)

    # 4. Найти группы дубликатов
    print("\n[4] Поиск групп дубликатов...")
    groups = get_duplicate_groups(cr)
    total_dups = sum(g['count'] for g in groups)
    total_to_delete = sum(len(g['delete_ids']) for g in groups)
    print(f"    Групп: {len(groups)}")
    print(f"    Книг в группах: {total_dups}")
    print(f"    К удалению: {total_to_delete}")

    # 5. Собрать m2m связи
    print("\n[5] Сбор m2m связей...")
    relations, old_to_keep = collect_m2m_relations(cr, groups)
    print(f"    Собрано {len(relations)} связей")

    # 6. Перенести m2m на keep_id
    print("\n[6] Перенос m2m связей на keep_id...")
    merge_m2m_relations(cr, relations, set(g['keep_id'] for g in groups))
    print("    m2m связи перенесены")

    # 7. Перепривязать units
    print("\n[7] Перепривязка units на keep_id...")
    units_updated = update_units_media_id(cr, old_to_keep)
    print(f"    Перепривязано {units_updated} экземпляров")

    # 8. Перепривязать movements
    print("\n[8] Перепривязка movements на keep_id...")
    movements_updated = update_movements(cr, old_to_keep)
    print(f"    Перепривязано {movements_updated} движений")

    # 9. Удалить вложения дубликатов
    print("\n[9] Удаление вложений дубликатов...")
    attachments_deleted = delete_duplicate_attachments(cr, old_to_keep)
    print(f"    Удалено {attachments_deleted} вложений")

    # 10. Удалить дубликаты op.media
    print("\n[10] Удаление дубликатов op.media...")
    deleted = delete_duplicates(cr, groups)
    print(f"    Удалено {deleted} дубликатов")

    # 11. Убрать UNIQUE constraints
    print("\n[11] Удаление UNIQUE constraints на op.media.isbn...")
    remove_unique_constraints(cr)

    # 12. Перенумеровать units
    print("\n[12] Перенумерация units...")
    renumbered = renumber_units(cr, groups)
    print(f"    Перенумеровано {renumbered} экземпляров")

    # 13. Валидация
    print("\n[13] Валидация...")
    is_valid = validate(cr)

    # 14. COMMIT
    print("\n[14] COMMIT...")
    conn.commit()
    print("  ✅ COMMIT выполнен")

    print("\n" + "=" * 70)
    print("МИГРАЦИЯ ЗАВЕРШЕНА")
    print(f"BKP таблицы: {BKP_PREFIX}*_{BKP_TIMESTAMP}")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    print("  ROLLBACK...")
    conn.rollback()
    print("  ROLLBACK выполнен. База в исходном состоянии.")
    sys.exit(1)

finally:
    cr.close()
    conn.close()
