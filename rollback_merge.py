#!/usr/bin/env python3
"""
Откат изменений из BKP таблиц.
Запуск: docker compose exec odoo python3 /mnt/extra-addons/rollback_merge.py
"""
import sys
import psycopg2

DB_CONFIG = {
    'host': 'db',
    'port': 5432,
    'dbname': 'test4',
    'user': 'odoo',
    'password': 'odoo',
}

def connect():
    return psycopg2.connect(**DB_CONFIG)

print("=" * 70)
print("ОТКАТ ИЗМЕНЕНИЙ")
print("=" * 70)

conn = connect()
conn.autocommit = False
cr = conn.cursor()

try:
    # Найти BKP таблицы
    cr.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name LIKE '_bkp_merge_%'
        ORDER BY table_name
    """)
    bkp_tables = [row[0] for row in cr.fetchall()]
    
    if not bkp_tables:
        print("BKP таблицы не найдены!")
        sys.exit(1)
    
    # Получить timestamp из имени (формат: _bkp_merge_<table>_YYYYMMDD_HHMMSS)
    ts = bkp_tables[0].split('_')[-2] + '_' + bkp_tables[0].split('_')[-1]
    print(f"Найдены BKP таблицы с timestamp: {ts}")
    
    # Удалить созданные нами таблицы/поля
    print("\n[1] Удаление op_media_isbn...")
    cr.execute("DROP TABLE IF EXISTS op_media_isbn CASCADE")
    
    print("[2] Удаление модели op.media.isbn из ir_model...")
    cr.execute("DELETE FROM ir_model WHERE model = 'op.media.isbn'")
    
    print("[3] Удаление полей из ir_model_fields...")
    cr.execute("DELETE FROM ir_model_fields WHERE model = 'op.media.isbn'")
    cr.execute("DELETE FROM ir_model_fields WHERE model = 'op.media' AND name = 'isbn_ids'")
    
    print("[4] Восстановление unique constraint на op_media.isbn...")
    cr.execute("ALTER TABLE op_media ADD CONSTRAINT op_media_isbn_uniq UNIQUE (isbn)")
    
    # Отключить FK constraints для восстановления
    print("\n[4.5] Отключение FK constraints...")
    tables = [
        'op_media',
        'op_media_unit',
        'op_media_movement',
        'op_course_op_media_rel',
        'op_media_op_subject_rel',
        'op_author_op_media_rel',
        'op_media_op_publisher_rel',
        'op_media_op_tag_rel',
    ]
    for table in tables + ['ir_attachment']:
        cr.execute(f"ALTER TABLE {table} DISABLE TRIGGER ALL")
    
    # Восстановить данные из BKP
    for i, table in enumerate(tables, 5):
        bkp = f"_bkp_merge_{table}_{ts}"
        print(f"[{i}] Восстановление {table} из {bkp}...")
        cr.execute(f"DELETE FROM {table}")
        cr.execute(f"INSERT INTO {table} SELECT * FROM {bkp}")
    
    # ir_attachment
    bkp = f"_bkp_merge_ir_attachment_{ts}"
    print(f"[{len(tables)+5}] Восстановление ir_attachment из {bkp}...")
    cr.execute("DELETE FROM ir_attachment WHERE res_model = 'op.media'")
    cr.execute(f"INSERT INTO ir_attachment SELECT * FROM {bkp}")
    
    # Включить FK constraints обратно
    print(f"[{len(tables)+6}] Включение FK constraints...")
    for table in tables + ['ir_attachment']:
        cr.execute(f"ALTER TABLE {table} ENABLE TRIGGER ALL")
    
    conn.commit()
    print("\n" + "=" * 70)
    print("ОТКАТ ЗАВЕРШЁН")
    print("=" * 70)

except Exception as e:
    conn.rollback()
    print(f"\nОШИБКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    cr.close()
    conn.close()
