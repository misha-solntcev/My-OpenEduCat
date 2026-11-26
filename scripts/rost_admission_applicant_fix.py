# -*- coding: utf-8 -*-
"""Приёмка: вернуть в partner_id заявителя (родителя) вместо ученика.

До 26.11.2026 enroll_student (ядро OpenEduCat) после зачисления
перезаписывал partner_id приёмки контактом УЧЕНИКА. Из-за этого вкладка
«Заявитель» показывала ребёнка, а «Телефон заявителя» и onchange
родительских данных искали не того человека. Код исправлен
(openeducat_admission/models/admission.py, enroll_student больше не
перезаписывает), но уже зачисленные приёмки остались с контактом
ученика — этот скрипт возвращает им родителя из op.parent.

Запуск (odoo shell, stdin-скриптом):
    docker compose exec -T odoo odoo shell -c /etc/odoo/odoo.conf \
        -d test4 --no-http < scripts/rost_admission_applicant_fix.py

По умолчанию DRY-RUN: только печатает, что будет изменено.
Запись — с переменной окружения ROST_APPLY=1:
    docker exec -e ROST_APPLY=1 -i odoo-dev-odoo-1 sh -c \
        'odoo shell -c /etc/odoo/odoo.conf -d test4 --no-http < /tmp/fix.py'

Идемпотентен: приёмки, у которых partner_id уже не контакт ученика,
пропускаются.
"""
import csv
import os
import sys

APPLY = os.environ.get('ROST_APPLY') == '1'
BACKUP = os.environ.get(
    'ROST_BACKUP', '/tmp/rost_admission_applicant_fix_backup.csv')


def out(*args):
    sys.stdout.write(' '.join(str(a) for a in args) + '\n')
    sys.stdout.flush()


Admission = env['op.admission']
rows = []
skipped = {'no_parent': 0}

for admission in Admission.search([]):
    student = admission.student_id
    if not student or admission.partner_id != student.partner_id:
        continue
    # is_student не годится как признак ручного заведения: ядро само
    # ставит его при зачислении (enroll_student, record.write).
    parent = student.parent_ids[:1]
    if not parent.partner_id:
        skipped['no_parent'] += 1
        continue
    rows.append((admission.id, admission.partner_id.id,
                 parent.partner_id.id, student.id,
                 admission.partner_id.name, parent.partner_id.name))

out('applicant_fix: mode=%s' % ('APPLY' if APPLY else 'DRY-RUN'))
out('applicant_fix: candidates=%d skipped: no_parent=%d'
    % (len(rows), skipped['no_parent']))
for row in rows[:20]:
    out('  admission %s: %s (id %s) -> %s (id %s)  [student %s]'
        % (row[0], row[4], row[1], row[5], row[2], row[3]))
if len(rows) > 20:
    out('  ... всего %d' % len(rows))

if APPLY and rows:
    with open(BACKUP, 'w', newline='', encoding='utf-8') as backup:
        writer = csv.writer(backup)
        writer.writerow(['admission_id', 'old_partner_id', 'new_partner_id',
                         'student_id', 'old_partner_name', 'new_partner_name'])
        writer.writerows(rows)
    out('applicant_fix: backup -> %s' % BACKUP)
    for admission_id, _old, new_id, _student, _old_name, _new_name in rows:
        Admission.browse(admission_id).partner_id = new_id
    env.cr.commit()
    out('applicant_fix: updated %d' % len(rows))
else:
    out('applicant_fix: nothing written (DRY-RUN)')

out('applicant_fix: DONE')
