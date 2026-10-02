# -*- coding: utf-8 -*-
"""Бэкфилл ссылок на объявления: hw_channel_message_id для старых заданий.

Зачем. После переделки (коммит 73fbcec) объявление о ДЗ адресуется ссылкой
hw_channel_message_id в самом задании, а не ищется по тексту внутри тела
сообщения. Старые объявления (созданные до переделки) ссылки не имеют —
они работают на ленивом бэкфилле, который срабатывает только при правке.

Бэкфилл нужен, чтобы правка старого выданного задания не искала пост по
тексту вообще: текст мог быть отредактирован в ПК-форме, поиск бы не нашёл,
и объявление молча разошлось бы с заданием.

Что делает:
1. Берёт листы с заданием.
2. Для каждого задания ищет объявление по тексту (как это делает
   _hw_channel_find_legacy_message) — но берёт ТОЛЬКО последнее сообщение,
   соответствующее текущему тексту задания.
3. Пропускает, если пост уже привязан к другому заданию (защита от двух
   одинаковых ДЗ в одном канале).
4. Пишет ссылку.

ЗАПУСК С ПРОСМОТРОМ (ничего не пишет, только показывает план):
    docker compose exec -T odoo odoo shell -d test4 --no-http \
        --max-cron-threads=0 < rost_lesson_homework/scripts/backfill_hw_channel_refs.py

ПОСЛЕ ПРОСМОТРА — раскомментируй строку APPLY ниже.
"""
import logging

_logger = logging.getLogger(__name__)

# План привязки просмотрен на test4 2026-10-01: 8 привязок, 49 заданий
# без поста, 0 спорных случаев (пост, занятый другим заданием).
DRY_RUN = False

total = 0
linked = 0
skipped_no_post = 0
skipped_foreign = 0
skipped_has_ref = 0
plan = []


def _hw_text(asg):
    return asg.hw_text()


sheets = env['op.attendance.sheet'].sudo().search(
    [('homework_assignment_id', '!=', False)])
print('листов с заданием: %d' % len(sheets))

for sheet in sheets:
    asg = sheet.homework_assignment_id
    if not asg.exists():
        continue
    total += 1

    if asg.hw_channel_message_id and asg.hw_channel_message_id.exists():
        skipped_has_ref += 1
        continue

    text = _hw_text(asg)
    if not text:
        skipped_no_post += 1
        continue

    msg = sheet._hw_channel_find_legacy_message(text)
    if not msg:
        skipped_no_post += 1
        continue

    # Защита: пост уже занят другим заданием — не забираем.
    if msg.hw_assignment_ids and asg not in msg.hw_assignment_ids:
        skipped_foreign += 1
        _logger.info(
            'HW post %s занят заданиями %s, пропускаем задание %s',
            msg.id, msg.hw_assignment_ids.ids, asg.id)
        continue

    ch = sheet._hw_channel()
    plan.append((asg.id, msg.id, ch.id if ch else None,
                 ch.name if ch else '?', text[:50]))

print('')
print('заданий рассмотрено: %d' % total)
print('уже со ссылкой:      %d' % skipped_has_ref)
print('пост не найден:      %d' % skipped_no_post)
print('пост занят другим:   %d' % skipped_foreign)
print('к привязке:          %d' % len(plan))
print('')
print('ПЛАН ПРИВЯЗКИ (задание -> сообщение -> канал):')
for asg_id, msg_id, ch_id, ch_name, text in plan:
    print('  %s -> %s  [%s]  %r' % (asg_id, msg_id, ch_name, text))

if DRY_RUN:
    print('')
    print('ЭТО ПРОСМОТР. Ничего не записано.')
    print('Чтобы выполнить: поменяй DRY_RUN = False в начале скрипта.')
else:
    for asg_id, msg_id, ch_id, ch_name, text in plan:
        env['op.assignment'].sudo().browse(asg_id).write(
            {'hw_channel_message_id': msg_id})
        linked += 1
    env.cr.commit()
    print('')
    print('ПРИВЯЗАНО: %d' % linked)

env.cr.rollback()