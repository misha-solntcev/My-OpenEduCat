# -*- coding: utf-8 -*-
"""Проверка прав на посещаемость: кто и когда попал в группы hr_attendance.

Зачем: 20.09.2026 в группы 316/317 (Officer / Administrator модуля
hr_attendance) одной пакетной операцией попали 110 человек — ученики,
учителя, родители. Из-за этого в меню у всех появился лишний пункт
«Посещаемость» от Odoo. 27.09.2026 состав починен, остались 4 админа.

Скрипт НИЧЕГО НЕ МЕНЯЕТ — только читает базу. Запускать перед и после
-u hr_attendance, а также если кто-то снова жалуется на лишний пункт
в меню.

Что считается тревожным:
  * много людей в 316/317 — значит кто-то прогнал скрипт наполнения;
  * одинаковый write_date у десятков людей — признак пакетной записи;
  * implied-связь, ведущая в 316/317 — группа тянет другую автоматически;
  * непустая hr.employee — следы импорта сотрудников.

Запуск:
    sudo -u odoo odoo shell -c /etc/odoo/odoo.conf -d rostschoolspb --no-http \
        < /tmp/check_hr_attendance_groups.py
"""
from collections import Counter

Group = env['res.groups'].sudo()          # noqa: F821
User = env['res.users'].sudo()            # noqa: F821
cr = env.cr                              # noqa: F821

HR_GROUPS = [(316, 'Officer: Управление посещаемостью'),
             (317, 'Administrator (Посещаемость)')]

# Кого ожидаем видеть: 4 админа школы.
EXPECTED_ADMINS = {2: 'Солнцев Михаил', 115: 'Барановский Виктор',
                   117: 'Солнцева Вера', 118: 'Макарова Надежда'}


def line(char='='):
    print(char * 72)


def group_members(gid):
    cr.execute("""
        SELECT r.uid, u.login, p.name::text, u.write_date,
               (SELECT count(*) FROM op_faculty f WHERE f.user_id = r.uid) AS fac,
               (SELECT count(*) FROM op_student s WHERE s.id = r.uid) AS stu
        FROM res_groups_users_rel r
        JOIN res_users u ON u.id = r.uid
        LEFT JOIN res_partner p ON p.id = u.partner_id
        WHERE r.gid = %s
        ORDER BY u.id
    """, (gid,))
    return cr.fetchall()


line()
print('ПРОВЕРКА ПРАВ НА ПОСЕЩАЕМОСТЬ (hr_attendance, группы 316/317)')
line()

problems = []
# Считаем ПО ЛЮДЯМ, а не по записям: один человек в двух группах иначе
# даст ложное «признак пакетной записи». Ожидаемых админов не считаем.
dates_by_uid = {}

for gid, title in HR_GROUPS:
    grp = Group.browse(gid)
    if not grp.exists():
        print('\nГРУППА %d НЕ СУЩЕСТВУЕТ' % gid)
        problems.append('группа %d отсутствует' % gid)
        continue

    rows = group_members(gid)
    line()
    print('ГРУППА %d — «%s»' % (gid, grp.name))
    print('  участников: %d' % len(rows))
    for uid, login, name, wdate, fac, stu in rows:
        role = 'учитель' if fac else ('ученик' if stu else '—')
        print('    uid=%-4s %-34s %-8s измён: %s' % (
            uid, (name or login or '?')[:34], role, wdate or '—'))
        if wdate:
            dates_by_uid[uid] = str(wdate)[:19]

    extra = [r for r in rows if r[0] not in EXPECTED_ADMINS]
    if len(extra) > 10:
        problems.append('в группе %d лишних людей: %d' % (gid, len(extra)))

# ---------------------------------------------------- признак пакетной записи
# Порог 5 человек с одинаковой секундой: 4 админа из одной пакетной
# операции — норма, отличать от 20.09 (110 человек) не спутать.
BATCH_MARK = 5
batch = Counter(dates_by_uid.values())
repeated = [(d, n) for d, n in batch.items() if n >= BATCH_MARK]
if repeated:
    line()
    print('ПРИЗНАК ПАКЕТНОЙ ЗАПИСИ (одинаковое время изменения, %d+ чел.):' % BATCH_MARK)
    for d, n in sorted(repeated, key=lambda x: -x[1])[:5]:
        print('    %s — %d чел.' % (d, n))
    problems.append('пакетная запись: %d чел. в одну секунду' % max(n for _d, n in repeated))

# ----------------------------------------------------------- implied-связи
line()
print('IMPLIED-СВЯЗИ, ВЕДУЩИЕ В 316/317:')
cr.execute("""
    SELECT r.gid, g.name::text, r.hid, h.name::text
    FROM res_groups_implied_rel r
    JOIN res_groups g ON g.id = r.gid
    JOIN res_groups h ON h.id = r.hid
    WHERE r.hid IN (316, 317)
    ORDER BY r.hid, r.gid
""")
links = cr.fetchall()
if links:
    for gid, gname, hid, hname in links:
        print('    группа %d «%s» → %d «%s»' % (gid, gname, hid, hname))
        problems.append('есть implied-связь %d → %d' % (gid, hid))
else:
    print('    нет — ни одна группа не тянет эти автоматически')

# ---------------------------------------------------------------- hr.employee
line()
cr.execute("""
    SELECT
      (SELECT count(*) FROM hr_employee),
      (SELECT count(*) FROM hr_employee WHERE user_id IS NOT NULL)
""")
if cr.description:
    total, linked = cr.fetchone()
    print('hr.employee: записей %s, из них с пользователем %s' % (total, linked))
    if total:
        problems.append('в базе есть hr.employee (%s записей)' % total)
else:
    print('hr.employee: модуль не установлен')

# -------------------------------------------------------------------- итог
line()
if problems:
    print('ИТОГ: есть замечания —')
    for p in problems:
        print('    - %s' % p)
    print('    разбирайтесь по шапке скрипта')
else:
    print('ИТОГ: чисто — в группах только админы, implied-связей нет.')
line()
print('ЗАВЕРШЕНО (ничего не изменено)')
line()
