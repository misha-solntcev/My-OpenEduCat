# -*- coding: utf-8 -*-
"""Миграция О3 -> свободная ячейка оценки (без потерь и без затирания).

Колонка О3 (grade_3) упразднена 4-оценочной схемой (О1, О2, ДЗ 1, ДЗ 2).
Оценки из О3 переносим в ПЕРВУЮ СВОБОДНУЮ ячейку строки:
    О1 пусто  -> grade_1
    О2 пусто  -> grade_2
    иначе     -> marks_2 (ДЗ 2), создав строку сдачи при отсутствии
Существующие оценки НЕ затираются: слот берётся только пустой.

Запуск НА ПРОДЕ, odoo shell, ДО `-u openeducat_attendance`
(иначе -u снесёт поле раньше, чем скрипт его прочитает):
    sudo -u odoo odoo shell -c /etc/odoo/odoo.conf -d rostschoolspb --no-http \
        < /tmp/migrate_grade3_free_slot.py

Идемпотентен: повторный запуск не находит grade_3>0 и ничего не делает.
Резервная копия значений — в op_attendance_line_grades_backup_20260926.
"""
from collections import Counter
from datetime import date as _date

Line = env['op.attendance.line']
Sub = env['op.assignment.sub.line']

lines = Line.search([('grade_3', '>', 0)])
print("=" * 72)
print("СТРОК С grade_3 > 0: %d" % len(lines))
print("=" * 72)

# start_date/end_date у года — объекты date, а не строки
today = _date.today()
cur = lines.filtered(
    lambda l: l.academic_year_id.start_date and l.academic_year_id.start_date <= today
    and l.academic_year_id.end_date and l.academic_year_id.end_date >= today)
print("из них текущий учебный год: %d, прошлые: %d" % (len(cur), len(lines) - len(cur)))

# --- сухая диагностика: куда уедет каждая оценка ---------------------
plan = Counter()
no_slot = 0
no_slot_rows = []
for line in lines:
    if line.grade_1 <= 0:
        plan['О1'] += 1
    elif line.grade_2 <= 0:
        plan['О2'] += 1
    else:
        asg = getattr(line.attendance_id, 'homework_assignment_id', False)
        if asg:
            sub = Sub.search([('assignment_id', '=', asg.id),
                              ('student_id', '=', line.student_id.id)], limit=1)
            if not sub or not sub.marks_2:
                plan['ДЗ 2'] += 1
            else:
                no_slot += 1
                no_slot_rows.append(line)
        else:
            no_slot += 1
            no_slot_rows.append(line)

print("\nПЛАН ПЕРЕНОСА:")
for slot in ('О1', 'О2', 'ДЗ 2'):
    if plan[slot]:
        print("  -> %-6s %d" % (slot, plan[slot]))
print("  НЕКУДА переносить (всё занято): %d" % no_slot)
if no_slot_rows:
    print("\n!!! ЭТИ ОЦЕНКИ ОСТАЮТСЯ В О3 (перенос невозможен):")
    for l in no_slot_rows[:20]:
        print("   %s %-24s %-16s О3=%-4s О1=%-4s О2=%s" % (
            l.attendance_date, (l.student_id.name or '')[:24],
            (l.subject_id.name or '')[:16], l.grade_3, l.grade_1, l.grade_2))

# --- перенос ------------------------------------------------------------
moved = {'О1': 0, 'О2': 0, 'ДЗ 2': 0}
skipped = 0
subs_created = 0

for line in lines:
    g3 = line.grade_3
    if line.grade_1 <= 0:
        line.write({'grade_1': g3, 'grade_3': 0.0})
        moved['О1'] += 1
    elif line.grade_2 <= 0:
        line.write({'grade_2': g3, 'grade_3': 0.0})
        moved['О2'] += 1
    else:
        asg = getattr(line.attendance_id, 'homework_assignment_id', False)
        sub = False
        if asg:
            sub = Sub.search([('assignment_id', '=', asg.id),
                              ('student_id', '=', line.student_id.id)], limit=1)
            if not sub:
                sub = Sub.create({
                    'assignment_id': asg.id,
                    'student_id': line.student_id.id,
                    'state': 'accept',
                })
                subs_created += 1
        if sub and not sub.marks_2:
            sub.write({'marks_2': g3})
            line.write({'grade_3': 0.0})
            moved['ДЗ 2'] += 1
        else:
            # всё занято или нет задания — НЕ затираем, оставляем в О3
            skipped += 1

env.cr.commit()
print("\n" + "=" * 72)
print("ГОТОВО (закоммичено)")
print("=" * 72)
print("Перенесено: О1=%d  О2=%d  ДЗ 2=%d  (всего %d)"
      % (moved['О1'], moved['О2'], moved['ДЗ 2'],
         moved['О1'] + moved['О2'] + moved['ДЗ 2']))
print("Создано строк сдачи: %d" % subs_created)
print("Осталось в О3 (некуда было переносить): %d" % skipped)
print("grade_3 > 0 в базе: %d" % Line.search_count([('grade_3', '>', 0)]))
