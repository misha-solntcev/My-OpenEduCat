# -*- coding: utf-8 -*-
"""Аккаунты родителям, у которых их нет (по почте контакта).

Зачем: на 13.11.2026 из 118 родителей аккаунт был только у 7 — вход в
систему у семьи исторически шёл через аккаунт ребёнка. Скрипт заводит
родительские аккаунты (внутренний юзер + группа «Родитель», child_ids =
аккаунты детей) по почте из карточки контакта. Детские аккаунты НЕ
трогает: семья просто получает второй вход.

Классификация кандидатов (op.parent без user_id):
  READY       — почты нет ни у одного юзера  -> создаём
  LINKABLE    — логин занят юзером ТОГО ЖЕ контакта (аккаунт родителя
                когда-то создали, но не связали с op.parent) -> связываем
                и донастраиваем (группа «Родитель», компания, child_ids)
  LOGIN_TAKEN — логин занят юзером ДРУГОГО контакта (обычно аккаунт
                ребёнка на почте родителя) -> НЕ создаём, нужен отдельный
                адрес; список отдаём пользователю
  NO_EMAIL    — почты в контакте нет -> нужен адрес от семьи

Режимы (env):
  PARENT_ACC_DRY=1     (по умолчанию) только отчёт, ничего не пишем
  PARENT_ACC_DRY=0     создавать аккаунты
  PARENT_ACC_INVITE=1  после создания отправить письмо-приглашение
                       (по умолчанию 0 — на test4 письма не шлём)

Отчёт пишется в /tmp/parent_accounts_report.csv (id, имя, почта, статус,
владелец занятого логина). Каждый аккаунт создаётся в своём savepoint:
одна ошибка не отменяет остальные.
"""
import csv
import os
import sys

DRY = os.environ.get('PARENT_ACC_DRY', '1') != '0'
INVITE = os.environ.get('PARENT_ACC_INVITE', '0') == '1'
REPORT = '/tmp/parent_accounts_report.csv'


def out(msg):
    sys.stdout.write(str(msg) + '\n')
    sys.stdout.flush()


P = env['op.parent'].sudo()
Users = env['res.users'].sudo()
parent_grp = env.ref('rost_school_access.group_op_parent_rost',
                     raise_if_not_found=False)

candidates = P.search([('user_id', '=', False)], order='id')
ready, linkable, taken, no_email = [], [], [], []

for parent in candidates:
    email = (parent.partner_id.email or '').strip()
    if not email:
        no_email.append((parent, '', ''))
        continue
    owner = Users.with_context(active_test=False).search(
        [('login', '=ilike', email)], limit=1)
    if owner and owner.partner_id.id == parent.partner_id.id:
        linkable.append((parent, email,
                         'user id=%s active=%s' % (owner.id, owner.active)))
    elif owner:
        kind = 'ученик' if env['op.student'].sudo().search_count(
            [('user_id', '=', owner.id)]) else 'другой юзер'
        taken.append((parent, email, '%s id=%s active=%s %s'
                      % (owner.login, owner.id, owner.active, kind)))
    else:
        ready.append((parent, email, ''))

out('режим: %s%s' % ('ОТЧЁТ (ничего не пишем)' if DRY else 'СОЗДАНИЕ АККАУНТОВ',
                     ', с приглашениями' if (not DRY and INVITE) else ''))
out('родителей без аккаунта: %s' % len(candidates))
out('  READY (создаём):            %s' % len(ready))
out('  LINKABLE (связываем):       %s' % len(linkable))
out('  LOGIN_TAKEN (нужен адрес):  %s' % len(taken))
out('  NO_EMAIL (нужен адрес):     %s' % len(no_email))

with open(REPORT, 'w', newline='') as fh:
    wr = csv.writer(fh)
    wr.writerow(['parent_id', 'name', 'email', 'status', 'detail'])
    for parent, email, _ in ready:
        wr.writerow([parent.id, parent.name, email, 'READY', ''])
    for parent, email, detail in linkable:
        wr.writerow([parent.id, parent.name, email, 'LINKABLE', detail])
    for parent, email, detail in taken:
        wr.writerow([parent.id, parent.name, email, 'LOGIN_TAKEN', detail])
    for parent, email, _ in no_email:
        wr.writerow([parent.id, parent.name, '', 'NO_EMAIL', ''])
out('отчёт: %s' % REPORT)

if DRY:
    for parent, email, detail in linkable:
        out('  связать: %-30s %-28s %s' % (parent.name[:30], email, detail))
    for parent, email, detail in taken[:5]:
        out('  занят:   %-30s %-28s %s' % (parent.name[:30], email, detail))
    for parent, _, _ in no_email[:5]:
        out('  без почты: %-30s id=%s' % (parent.name[:30], parent.id))
    raise SystemExit(0)


def link_existing(parent):
    """Связать существующий аккаунт того же контакта с карточкой родителя."""
    owner = Users.with_context(active_test=False).search(
        [('login', '=ilike', (parent.partner_id.email or '').strip())],
        limit=1)
    groups = [(4, env.ref('base.group_user').id)]
    if parent_grp:
        groups.append((4, parent_grp.id))
    vals = {'groups_id': groups}
    if 'is_parent' in owner._fields:
        vals['is_parent'] = True
    if not owner.company_ids:
        vals['company_ids'] = [(6, 0, [(owner.company_id or env.company).id])]
    owner.write(vals)
    parent.user_id = owner.id
    child_users = [s.user_id.id for s in parent.student_ids if s.user_id]
    if child_users:
        owner.child_ids = [(6, 0, child_users)]
    return owner


created, linked, errors = 0, 0, []
for parent, email, _ in ready:
    try:
        with env.cr.savepoint():
            parent.create_parent_user()
        created += 1
    except Exception as exc:
        errors.append((parent.id, parent.name, '%s: %s'
                       % (type(exc).__name__, str(exc).strip()[:120])))

for parent, email, _ in linkable:
    try:
        with env.cr.savepoint():
            link_existing(parent)
        linked += 1
    except Exception as exc:
        errors.append((parent.id, parent.name, 'LINK %s: %s'
                       % (type(exc).__name__, str(exc).strip()[:120])))

env.cr.commit()
out('создано аккаунтов: %s' % created)
out('связано существующих: %s' % linked)
out('ошибок: %s' % len(errors))
for row in errors[:10]:
    out('  %s %s -> %s' % row)

if INVITE:
    sent, failed = 0, []
    for parent, _, _ in ready:
        parent.invalidate_recordset()
        if not parent.user_id:
            continue
        try:
            parent.user_id.sudo()._rost_send_invite('parent',
                                                   raise_failure=False)
            sent += 1
        except Exception as exc:
            failed.append((parent.id, str(exc)[:80]))
    out('приглашений отправлено: %s, сбоев: %s' % (sent, len(failed)))

still = P.search_count([('user_id', '=', False)])
out('родителей без аккаунта теперь: %s' % still)
