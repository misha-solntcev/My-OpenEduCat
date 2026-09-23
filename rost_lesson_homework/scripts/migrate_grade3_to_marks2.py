# -*- coding: utf-8 -*-
"""Миграция: оценки из колонки О3 (grade_3) -> вторая оценка ДЗ (marks_2).

Запускать НА ПРОДЕ ДО `-u openeducat_attendance`, odoo shell:
(см. комментарий в конце файла с порядком деплоя)
Идемпотентен: переносит только строки, где grade_3 > 0 и у урока есть
задание. Сдачи нет — создаёт (state='accept', приём без сдачи).
grade_3 обнуляется после переноса; колонка пока остаётся в БД (поле
DEPRECATED в модели), удалим отдельным шагом после проверки переноса.
"""
marks_migrated = 0
subs_created = 0
skipped_no_asg = 0

lines = env['op.attendance.line'].search([('grade_3', '>', 0)])
print("LINES_WITH_GRADE_3: %d" % len(lines))

for line in lines:
    sheet = line.attendance_id
    asg = getattr(sheet, 'homework_assignment_id', False)
    if not asg:
        skipped_no_asg += 1
        continue
    sub = env['op.assignment.sub.line'].search([
        ('assignment_id', '=', asg.id),
        ('student_id', '=', line.student_id.id),
    ], limit=1)
    if not sub:
        sub = env['op.assignment.sub.line'].create({
            'assignment_id': asg.id,
            'student_id': line.student_id.id,
            'state': 'accept',
            'marks_2': line.grade_3,
        })
        subs_created += 1
    else:
        # marks_2 не затирать, если уже стоит; marks пуста — О3 туда не кладём
        if not sub.marks_2:
            sub.write({'marks_2': line.grade_3})
    line.write({'grade_3': 0.0})
    marks_migrated += 1

env.cr.commit()
print("MIGRATED=%d SUBS_CREATED=%d SKIPPED_NO_ASSIGNMENT=%d" % (
    marks_migrated, subs_created, skipped_no_asg))
