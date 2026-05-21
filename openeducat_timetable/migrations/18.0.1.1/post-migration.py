from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """
    Автоматическая миграция данных при обновлении модуля.
    Выполняется после (post) обновления структуры таблиц.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # 1. Заполняем timetable_date на основе start_datetime
    cr.execute("""
        UPDATE op_session 
        SET timetable_date = (start_datetime AT TIME ZONE 'UTC' AT TIME ZONE 'UTC')::date
        WHERE timetable_date IS NULL
    """)

    # 2. Сопоставляем уроки с сеткой звонков (timing_id)
    cr.execute("SELECT id, start_datetime FROM op_session WHERE timing_id IS NULL")
    sessions_data = cr.fetchall()
    
    if not sessions_data:
        return

    timings = env['op.timing'].search([])
    if not timings:
        return

    for session_id, start_datetime in sessions_data:
        if not start_datetime:
            continue
            
        h, m = start_datetime.hour, start_datetime.minute
        match = timings.filtered(lambda t: t.lesson_hour == h and t.lesson_minute == m)
        if match:
            cr.execute("UPDATE op_session SET timing_id = %s WHERE id = %s", (match[0].id, session_id))