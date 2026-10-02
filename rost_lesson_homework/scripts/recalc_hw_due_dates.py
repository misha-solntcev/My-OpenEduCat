# -*- coding: utf-8 -*-
"""Пересчёт сроков выданных ДЗ по новому правилу.

Правило (2026-10-02): срок сдачи — конец урока, СЛЕДУЮЩЕГО за ближайшим.

Зачем. Срок считался в _next_lesson_datetime при СОЗДАНИИ задания и при
выдаче. Задания, выданные до изменения правила, сохранили старый срок —
конец ближайшего урока, взятый как его НАЧАЛО. То есть срок совпадал с
началом урока, на котором ДЗ ещё только выдают.

Пересчитывает только задания, у которых есть лист урока (лист знает
учителя, предмет и класс, по которым ищется следующий урок). Задания без
листа (созданные в ПК-форме, 29 из 86) не трогаем: срок у них поставлен
учителем руками, и пересчитывать его по расписанию нельзя — там может
быть произвольная дата.

DRY_RUN сначала показывает план и ждёт подтверждения.
"""
import sys

DRY_RUN = False  # план просмотрен на test4 2026-10-02: 12 заданий

out = []
plan = []
skipped_no_sheet = 0
skipped_manual = 0
skipped_cancel = 0
unchanged = 0

sheets = env['op.attendance.sheet'].sudo().search(
    [('homework_assignment_id', '!=', False)])
out.append('листов с заданием: %d' % len(sheets))

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
    new_due = sheet._next_lesson_datetime()
    if not new_due:
        skipped_manual += 1
        continue
    old_due = asg.submission_date
    if old_due == new_due:
        unchanged += 1
        continue
    plan.append((asg.id, asg.state, old_due, new_due,
                 sheet.subject_id.name or '', sheet.batch_id.name or ''))

out.append('без листа (срок вручную): %d' % skipped_no_sheet)
out.append('отменённых: %d' % skipped_cancel)
out.append('без срока: %d' % skipped_manual)
out.append('уже по новому правилу: %d' % unchanged)
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