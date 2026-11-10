# -*- coding: utf-8 -*-
"""Пересчёт сроков выданных ДЗ по новому правилу.

Правило (2026-11-10): срок сдачи — начало СЛЕДУЮЩЕГО урока по расписанию
(первая сессия не в день текущего урока; вторая пара того же дня — ещё
тот же урок).

Зачем. Правка 02.10.2026 (bfa9b43/a21fa15) брала ВТОРУЮ будущую сессию
(limit=2, sessions[-1]) вместо первой: домен `start_datetime > max(start,
now)` уже исключал собственный урок, и срок уезжал на урок через один.
На проде 119 из 514 выданных ДЗ с таким сроком (жалобы учителей
10.11.2026). Фикс в _next_lesson_datetime пересчитывает новые выдачи,
уже выданным нужен этот скрипт.

Пересчитывает только задания, у которых есть лист урока (лист знает
учителя, предмет и класс, по которым ищется следующий урок), в состоянии
publish (ждёт сдачи) и с непрошедшим сроком. Задания без листа
(созданные в ПК-форме) не трогаем: срок у них поставлен учителем руками,
и пересчитывать его по расписанию нельзя — там может быть произвольная
дата. Черновики пропускаем: hw_publish пересчитывает срок при выдаче.
finish и просроченные не трогаем: это уже история (сдано/проверено),
перенос их срока на будущий урок воскресил бы старую домашку как
активную.

DRY_RUN сначала показывает план и ждёт подтверждения.
"""
import sys

from odoo import fields

DRY_RUN = True  # план просматривать ДО записи; False — только после просмотра

out = []
plan = []
skipped_no_sheet = 0
skipped_manual = 0
skipped_cancel = 0
skipped_state = 0
skipped_past = 0
unchanged = 0

sheets = env['op.attendance.sheet'].sudo().search(
    [('homework_assignment_id', '!=', False)])
out.append('листов с заданием: %d' % len(sheets))

now = fields.Datetime.now()
for sheet in sheets:
    asg = sheet.homework_assignment_id
    if not asg.exists():
        continue
    if asg.state == 'cancel':
        skipped_cancel += 1
        continue
    # Задание без листа — срок мог поставить учитель вручную, не трогаем.
    if not sheet.session_id:
        skipped_no_sheet += 1
        continue
    # Черновик пересчитается при выдаче, finish — проверенная история.
    if asg.state != 'publish':
        skipped_state += 1
        continue
    old_due = asg.submission_date
    # Просроченные не трогаем: правильный срок всегда РАНЬШЕ неверного,
    # значит неверный прошедший срок — уже свершившаяся история.
    if not old_due or old_due <= now:
        skipped_past += 1
        continue
    new_due = sheet._next_lesson_datetime()
    if not new_due:
        skipped_manual += 1
        continue
    if old_due == new_due:
        unchanged += 1
        continue
    plan.append((asg.id, asg.state, old_due, new_due,
                 sheet.subject_id.name or '', sheet.batch_id.name or ''))

out.append('без листа (срок вручную): %d' % skipped_no_sheet)
out.append('отменённых: %d' % skipped_cancel)
out.append('черновиков/finish (срок пересчитается сам / история): %d'
           % skipped_state)
out.append('просроченных (история, не трогаем): %d' % skipped_past)
out.append('без срока: %d' % skipped_manual)
out.append('уже по правилу: %d' % unchanged)
out.append('к пересчёту: %d' % len(plan))
out.append('')
out.append('ЗАДАНИЕ  СОСТОЯНИЕ  БЫЛО -> СТАЛО  ПРЕДМЕТ/КЛАСС')
for asg_id, state, old_due, new_due, subj, batch in plan:
    out.append('%s  %s  %s -> %s  %s / %s'
               % (asg_id, state, old_due, new_due, subj, batch))

if DRY_RUN:
    out.append('')
    out.append('ЭТО ПРОСМОТР. Ничего не записано.')
else:
    for asg_id, state, old_due, new_due, subj, batch in plan:
        env['op.assignment'].sudo().browse(asg_id).write(
            {'submission_date': new_due})
    env.cr.commit()
    out.append('')
    out.append('ПЕРЕСЧИТАНО: %d' % len(plan))

sys.stderr.write('RESULT\n' + '\n'.join(out) + '\n')
env.cr.rollback()