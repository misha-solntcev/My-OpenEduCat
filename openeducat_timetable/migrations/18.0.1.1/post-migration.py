from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """
    Автоматическая миграция данных. 
    Используем SQL для корректной обработки часовых поясов.
    """
    # 1. Определяем часовой пояс школы (сетка уроков 09:30 и т.д. создана в нем)
    # Даже если сервер в облаке, а вы в Иркутске, сопоставляем с МСК
    tz_school = 'Europe/Moscow'

    # 2. Обновляем timetable_date (Дата урока)
    # Конвертируем UTC из базы в локальное время школы, чтобы дата была верной
    cr.execute("""
        UPDATE op_session 
        SET timetable_date = (start_datetime AT TIME ZONE 'UTC' AT TIME ZONE %s)::date
        WHERE timetable_date IS NULL AND start_datetime IS NOT NULL
    """, (tz_school,))

    # 3. Привязываем уроки к сетке звонков (timing_id)
    # Сравниваем часы и минуты начала урока (в МСК) с часами и минутами в op_timing
    query_timing = """
        UPDATE op_session sess
        SET timing_id = t.id
        FROM op_timing t
        WHERE sess.timing_id IS NULL 
          AND sess.start_datetime IS NOT NULL
          AND t.lesson_hour = EXTRACT(HOUR FROM sess.start_datetime AT TIME ZONE 'UTC' AT TIME ZONE %s)
          AND t.lesson_minute = EXTRACT(MINUTE FROM sess.start_datetime AT TIME ZONE 'UTC' AT TIME ZONE %s)
    """
    cr.execute(query_timing, (tz_school, tz_school))
    
    # 4. Логируем результат в лог сервера (опционально)
    # Это поможет при деплое увидеть, сколько записей подхватилось
    row_count = cr.rowcount
    # print/logging здесь обычно не виден, но можно оставить для отладки