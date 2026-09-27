# -*- coding: utf-8 -*-
"""Разовый пересчёт stored-полей: grade_avg и агрегаты листов.

Зачем: grade_avg и агрегаты op.attendance.sheet — stored=True compute.
При массовом изменении состава оценок (в т.ч. удаление полей
x_mark / x_behavior 06.05.2026) они остались с прежними значениями:
на проде найдено 43 строки с расхождением и 15 листов, где сохранённая
статистика не совпадает с фактической.

Пересчёт идёт по ВСЕЙ базе, но трогает только stored-значения — сами
оценки (grade_1/grade_2/marks/marks_2) не изменяются.

Запуск:
    sudo -u odoo odoo shell -c /etc/odoo/odoo.conf -d rostschoolspb --no-http \
        < /tmp/recompute_grade_stats.py
"""
import logging
from datetime import date as _date

_logger = logging.getLogger('rost.recompute')

Line = env['op.attendance.line'].sudo()
Sheet = env['op.attendance.sheet'].sudo()
today = _date.today()

# ---------------------------------------------------------------- grade_avg
# В Odoo префиксное ИЛИ: '|' ставится ПЕРЕД операндами, которые объединяет.
lines = Line.search(['|', ('grade_1', '>', 0), ('grade_2', '>', 0)])
print("=" * 72)
print("СТРОК С ОБЫЧНЫМИ ОЦЕНКАМИ: %d" % len(lines))
print("=" * 72)

fixed_avg = 0
for i, rec in enumerate(lines, 1):
    rec.invalidate_recordset(['grade_avg'])
    before = rec.grade_avg
    rec._rost_compute_grade_avg()
    after = rec.grade_avg
    if abs(before - after) > 0.001:
        fixed_avg += 1
        if fixed_avg <= 20:
            print("  id=%s %s %-22s было %.2f -> стало %.2f" % (
                rec.id, rec.attendance_date,
                (rec.student_id.name or '')[:22], before, after))
    if i % 2000 == 0:
        _logger.info("grade_avg: %s/%s", i, len(lines))
        print("  ... %d/%d" % (i, len(lines)))

print("\nИСПРАВЛЕНО grade_avg: %d" % fixed_avg)

# ---------------------------------------------------------- агрегаты листов
# Отбор: листы с ОБЫЧНЫМИ оценками ИЛИ с листом, у которого задание ДЗ
# назначено и есть строки сдачи. Раньше стоял только первый критерий, и
# лист 9023 от 25.09.2026 (Литература, 5А — пять оценок только за ДЗ,
# обычных нет) выпадал из пересчёта: агрегаты оставались нулевыми.
sheets = Sheet.search(['|',
                       ('attendance_line.grade_1', '>', 0),
                       ('homework_assignment_id', '!=', False)])
print("\n" + "=" * 72)
print("ЛИСТОВ К ПЕРЕСЧЁТУ: %d" % len(sheets))
print("=" * 72)

fixed_sheet = 0
for i, sh in enumerate(sheets, 1):
    sh.invalidate_recordset(
        ['count_5', 'count_4', 'count_3', 'count_2', 'average_grade_lesson'])
    before = (sh.count_5, sh.count_4, sh.count_3, sh.count_2,
              round(sh.average_grade_lesson or 0.0, 2))
    sh._rost_compute_all_stats()
    after = (sh.count_5, sh.count_4, sh.count_3, sh.count_2,
             round(sh.average_grade_lesson or 0.0, 2))
    if before != after:
        fixed_sheet += 1
        if fixed_sheet <= 20:
            print("  лист=%s %s %s -> %s" % (
                sh.id, sh.attendance_date, before, after))
    if i % 500 == 0:
        _logger.info("sheets: %s/%s", i, len(sheets))
        print("  ... %d/%s" % (i, len(sheets)))

print("\nИСПРАВЛЕНО ЛИСТОВ: %d" % fixed_sheet)

# --------------------------------------------- листы с нулевой статистикой
print("\n" + "=" * 72)
print("ПРОВЕРКА: листы с оценками, но с нулевой статистикой")
print("=" * 72)
# Отбор тот же, что и при пересчёте: обычные оценки ИЛИ назначенное
# задание ДЗ. Условие «нулевая статистика» накладываем в Python — в домене
# второй префиксный '|' применился бы ко ВСЕМУ выражению, а не к этой паре.
bad = Sheet.search(['|',
                    ('attendance_line.grade_1', '>', 0),
                    ('homework_assignment_id', '!=', False)])
bad = bad.filtered(
    lambda s: not (s.count_5 or s.count_4 or s.count_3 or s.count_2))
for sh in bad[:10]:
    marks = 0
    for l in sh.attendance_line:
        if l.grade_1 and 2 <= l.grade_1 <= 5:
            marks += 1
        if l.grade_2 and 2 <= l.grade_2 <= 5:
            marks += 1
        if l.hw_sub_line_id:
            for v in (l.hw_sub_line_id.marks, l.hw_sub_line_id.marks_2):
                if v and 2 <= v <= 5:
                    marks += 1
    print("  лист=%s %s оценок на самом деле: %d" % (
        sh.id, sh.attendance_date, marks))
print("  таких листов осталось: %d" % len(bad))

env.cr.commit()
print("\n" + "=" * 72)
print("ЗАКОММИЧЕНО")
print("=" * 72)
