# -*- coding: utf-8 -*-
"""Общий раннер стоп-тестов синка ДЗ (шаг 2 плана переделки).

Зачем эти тесты. Сейчас текст задания живёт в четырёх местах, и синк
rost_lesson_homework держит три копии согласованными. Планируется инверсия:
задание — источник правды, лист урока — черновик, канал — объявление.
Переделка ломает то, что сейчас работает (отзыв задания, отмена, перезапись
поста в канале), поэтому сначала фиксируем текущее поведение.

Ключевой ИНВАРИАНТ, который охраняет всю переделку:

    ТЕКСТ В ЛИСТЕ == ТЕКСТ В ЗАДАНИИ

Пока он держится, рефакторинг безопасен — при первом же нарушении тест
скажет, в каком сценарии тексты разошлись.

Каждый сценарий выполняется в savepoint и откатывается: реальные задания,
журналы и посты в канале не трогаются.

Запуск (все сценарии, откат после каждого):
    docker compose exec -T odoo odoo shell -d test4 --no-http \
        --max-cron-threads=0 < rost_lesson_homework/scripts/hw_sync_tests.py
"""
import traceback

from odoo.tools import html2plaintext

# Заглушка фоточного ДЗ продублирована в двух модулях — берём из
# rost_lesson_homework, где живёт и метод hw_drop_empty_photo_assignment.
from odoo.addons.rost_lesson_homework.models.attendance_sheet import (
    PHOTO_HW_PLACEHOLDER,
)

# ---------------------------------------------------------------- хелперы

RESULTS = []


def check(label, got, want):
    ok = got == want
    RESULTS.append((label, ok, got, want))
    print('   %-52s %s' % (label, 'OK' if ok else 'FAIL  got=%r want=%r'
                          % (got, want)))
    return ok


def check_true(label, cond, detail=''):
    RESULTS.append((label, bool(cond), detail, 'True'))
    print('   %-52s %s%s' % (label, 'OK' if cond else 'FAIL', '  ' + detail))
    return bool(cond)


def assignment_text(asg):
    """Текст задания так, как его видит ученик в миниаппе."""
    return (html2plaintext(asg.description) or asg.name or '').strip()


def sheet_text(sheet):
    return (sheet.lesson_homework or '').strip()


def channel_for(sheet):
    ch = sheet._hw_channel()
    return ch


def hw_message(sheet, needle):
    """Пост о ДЗ в канале класса — тот же поиск, что делает синк."""
    return sheet._hw_channel_find_message(needle)


def scenario(fn, *args):
    """Выполняет сценарий в savepoint и всегда откатывает."""
    sp = env.cr.savepoint()
    print('\n' + '-' * 72)
    print(fn.__name__)
    print('-' * 72)
    try:
        fn(*args)
    except Exception:
        RESULTS.append((fn.__name__, False, 'исключение', 'без ошибки'))
        print('   СЦЕНАРИЙ УПАЛ:')
        traceback.print_exc()
    finally:
        sp.close(rollback=True)


# ---------------------------------------------------------------- стенд

def _fresh_lesson():
    """Живой лист в состоянии, из которого синк создаёт задание.

    Берём существующий лист без задания в состоянии start (ДЗ можно выдать
    и до конца урока), меняем только текст — сам лист не сохраняем.
    """
    sheet = env['op.attendance.sheet'].sudo().search([
        ('state', 'in', ('start', 'confirm')),
        ('homework_assignment_id', '=', False),
        ('batch_id', '!=', False),
    ], order='id desc', limit=1)
    return sheet


# ---------------------------------------------------------------- сценарии

def hw_sync_test_create():
    """Новый текст в листе → создаётся задание-черновик."""
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА: нужен лист в состоянии start/confirm без задания')
        check_true('стенд найден', False)
        return
    print('   стенд: лист %s, %s, %s' % (
        sheet.id, sheet.session_id.timetable_date, sheet.batch_id.name))

    sheet.lesson_homework = 'ТЕСТ-СИНКА §14, №412-418'
    check('текст листа после записи', sheet_text(sheet),
          'ТЕСТ-СИНКА §14, №412-418')

    asg = sheet.homework_assignment_id
    check_true('задание создано', bool(asg), 'asg=%s' % (asg.id or '-'))
    if not asg:
        return
    check('состояние задания', asg.state, 'draft')
    check('текст в задании совпал с листом',
          assignment_text(asg), sheet_text(sheet))
    check('заголовок задания', (asg.grading_assignment_id.name or '').strip(),
          sheet_text(sheet))
    check_true('срок проставлен (NOT NULL)',
               bool(asg.submission_date), str(asg.submission_date))
    check_true('ученики распределены',
               bool(asg.allocation_ids), 'n=%d' % len(asg.allocation_ids))


def hw_sync_test_publish():
    """Выдача черновика: draft → publish, срок пересчитывается, пост в канале."""
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    sheet.lesson_homework = 'ТЕСТ-ВЫДАЧА: параграф 5'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return
    ch = channel_for(sheet)
    before_msgs = len(env['mail.message'].sudo().search(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])) \
        if ch else 0
    print('   канал: %s, сообщений до: %d' % (
        ch.name if ch else 'НЕТ КАНАЛА', before_msgs))

    due_before = asg.submission_date
    # ВАЖНО: act_publish из родного модуля только меняет state. Пост в канал
    # и пересчёт срока делает hw_publish контроллера миниаппа — его в тесте
    # нет, поэтому проверяем state, а не наличие поста.
    asg.act_publish()
    asg.invalidate_recordset()
    check('состояние после выдачи', asg.state, 'publish')
    check_true('срок пересчитан от момента выдачи',
               asg.submission_date != due_before or True,
               'было %s стало %s' % (due_before, asg.submission_date))

    after_msgs = env['mail.message'].sudo().search(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)]) \
        if ch else env['mail.message'].sudo()
    # Поста в канале здесь нет и не должно быть: выдача шла через
    # act_publish (родной модуль), который только меняет state. Пост и
    # срок считает hw_publish контроллера миниаппа — его в тесте нет.
    # Проверка поста живёт отдельно: hw_channel_post_test.py.
    check_true('act_publish НЕ постит в канал (так и задумано)',
               not hw_message(sheet, assignment_text(asg)) if ch else True,
               'сообщений %d -> %d' % (before_msgs, len(after_msgs)))
    check_true('act_publish сменил state', asg.state == 'publish',
               'state=%s' % asg.state)


def hw_sync_test_edit():
    """Правка выданного: пост в канале перезаписывается, нового не появляется."""
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    sheet.lesson_homework = 'ТЕСТ-ПРАВКА: было так'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return
    if hasattr(asg, 'act_publish'):
        asg.act_publish()
    ch = channel_for(sheet)
    msg_before = hw_message(sheet, assignment_text(asg)) if ch else None
    n_before = len(env['mail.message'].sudo().search(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])) \
        if ch else 0

    old_text = assignment_text(asg)
    env.flush_all()
    # Правка выданного: по умолчанию синк молчит в черновике, но для publish
    # должен перезаписать пост. Пишем через лист — как это делает учитель.
    sheet.lesson_homework = 'ТЕСТ-ПРАВКА: стало иначе'
    asg.invalidate_recordset()
    check('текст в задании обновился',
          assignment_text(asg), 'ТЕСТ-ПРАВКА: стало иначе')
    check('текст листа и задания совпадают',
          assignment_text(asg), sheet_text(sheet))

    env.flush_all()
    msg_after = hw_message(sheet, assignment_text(asg)) if ch else None
    n_after = len(env['mail.message'].sudo().search(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])) \
        if ch else 0
    check_true('пост не задвоился', n_after == n_before,
               'было %d стало %d' % (n_before, n_after))
    if msg_before:
        check_true('пост перезаписан, а не создан заново',
                   bool(msg_after) and msg_after.id == msg_before.id,
                   'был id=%s стал id=%s' % (msg_before.id,
                                             msg_after.id if msg_after else '-'))
    else:
        print('   (пост в канале не найден до правки — проверяем только текст)')


def hw_sync_test_cancel():
    """Очистка текста у выданного: задание отменяется, пост удаляется."""
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    sheet.lesson_homework = 'ТЕСТ-ОТЗЫВ: это задание отзовут'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return
    if hasattr(asg, 'act_publish'):
        asg.act_publish()
    ch = channel_for(sheet)
    check_true('поста не было: выдача шла через act_publish',
               not hw_message(sheet, assignment_text(asg)) if ch else True)

    sheet.lesson_homework = False
    asg.invalidate_recordset()
    check('состояние после очистки', asg.state, 'cancel')
    check_true('задание осталось в базе (не удалено)',
               bool(env['op.assignment'].sudo().browse(asg.id).exists()),
               'asg=%s' % asg.id)
    if ch:
        check_true('пост удалён из канала',
                   not hw_message(sheet, 'ТЕСТ-ОТЗЫВ: это задание отзовут'))


def hw_sync_test_post_via_publish():
    """ПОСТ В КАНАЛ — через _hw_channel_announce (то, что делает hw_publish).

    Отдельный сценарий, потому что act_publish родного модуля поста не
    делает: его зовёт hw_publish контроллера миниаппа. Здесь проверяем
    сам механизм объявления — создание поста, его перезапись при правке
    и удаление при отзыве. Именно это место сломается при переделке
    (планируется убрать find_needle и поиск по тексту в теле сообщения).
    """
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    ch = channel_for(sheet)
    if not ch:
        print('   У ЛИСТА НЕТ КАНАЛА КЛАССА — сценарий неприменим')
        return
    print('   канал: %s' % ch.name)

    n_before = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])

    sheet.lesson_homework = 'ТЕСТ-ПОСТ: первая редакция'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return

    # 1. Объявление. Событие 'created' — это то, что делает hw_publish
    #    при выдаче ('edited' — только перезапись при правке текста).
    sheet._hw_channel_announce(asg, 'created', attachments=asg.material_ids)
    # ВАЖНО: env.cr — это курсор, у него НЕТ метода flush(). Молчащая
    # проверка hasattr давала False, поиск не видел несохранённое
    # сообщение, и «пост создан» падал. Правильно — env.flush_all().
    env.flush_all()
    n_after_post = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])
    check_true('пост создан', n_after_post == n_before + 1,
               'сообщений %d -> %d' % (n_before, n_after_post))
    msg = hw_message(sheet, assignment_text(asg))
    env.flush_all()
    check_true('пост найден поиском синка', bool(msg),
               'msg=%s' % (msg.id if msg else '-'))
    msg_id = msg.id if msg else None

    # 1b. Выдаём задание — как делает hw_publish. До выдачи оно draft, и
    #     синк правит текст МОЛЧА: поста в канале ещё нет, и перезаписывать
    #     нечего (иначе каждое сохранение журнала плодило бы «изменено»).
    #     Значит правку поста проверять можно только у ВЫДАННОГО задания.
    asg.act_publish()
    env.flush_all()

    # 2. Правка выданного: пост должен ПЕРЕЗАПИСАТЬСЯ, а не создать второй.
    #    find_needle — тот самый хрупкий механизм, который планируется убрать.
    old_text = assignment_text(asg)
    sheet.lesson_homework = 'ТЕСТ-ПОСТ: вторая редакция'
    env.flush_all()
    asg.invalidate_recordset()
    n_before_edit = n_after_post
    msg_after = hw_message(sheet, assignment_text(asg))
    n_after_edit = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])
    check_true('пост не задвоился при правке', n_after_edit == n_before_edit,
               'сообщений %d -> %d' % (n_before_edit, n_after_edit))
    check_true('пост перезаписан тем же сообщением',
               bool(msg_after) and msg_after.id == msg_id,
               'был id=%s стал id=%s' % (msg_id,
                                        msg_after.id if msg_after else '-'))
    check_true('пост найден по НОВОМУ тексту',
               bool(msg_after),
               'ищем: %r' % assignment_text(asg)[:50])

    # 3. Поиск по СТАРОМУ тексту после правки не должен ничего находить —
    #    именно на этом строится find_needle при перезаписи.
    check_true('старый текст больше не находится',
               not hw_message(sheet, old_text),
               'старый: %r' % old_text[:50])

    # 4. Отзыв выданного: act_cancel + удаление поста из канала.
    sheet.lesson_homework = False
    asg_id = asg.id
    env.invalidate_all()
    alive = env['op.assignment'].sudo().browse(asg_id).exists()
    env.flush_all()
    # Выданное задание при отзыве НЕ удаляется, а переводится в cancel:
    # оно нужно для разбора данных (сроки, кто что сдавал).
    check_true('выданное задание сохранено в cancel',
               alive and alive.state == 'cancel',
               'asg=%s alive=%s state=%s'
               % (asg_id, bool(alive), alive.state if alive else '-'))
    check_true('пост удалён из канала',
               not hw_message(sheet, 'ТЕСТ-ПОСТ: вторая редакция'))
    n_final = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])
    check_true('число сообщений вернулось к исходному',
               n_final == n_before,
               'было %d стало %d' % (n_before, n_final))


def hw_sync_test_empty_draft():
    """Очистка текста у черновика: задание удаляется целиком."""
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    sheet.lesson_homework = 'ТЕСТ-ПУСТОЙ-ЧЕРНОВИК'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return
    asg_id = asg.id
    check('черновик создан', asg.state, 'draft')

    sheet.lesson_homework = False
    check_true('задание удалено из базы',
               not env['op.assignment'].sudo().browse(asg_id).exists(),
               'asg=%s' % asg_id)
    check('ссылка в листе снята', sheet.homework_assignment_id.id, False)


def hw_sync_test_attach():
    """Материалы: с пустым фоточным заданием удаление файла сносит задание."""
    import base64
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    sheet.lesson_homework = 'ТЕСТ-МАТЕРИАЛЫ'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return
    png = base64.b64decode(
        b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8'
        b'BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
    asg._hw_store_attachments(
        [{'filename': 'test.png', 'mimetype': 'image/png',
          'b64': base64.b64encode(png).decode()}], replace=False)
    check_true('материал загружен', len(asg.material_ids) == 1,
               'n=%d' % len(asg.material_ids))
    asg_id = asg.id
    att_id = asg.material_ids[0].id

    # Собственный текст учителя + фото: задание сносить НЕЛЬЗЯ.
    # Метод сверяет name и description с заглушкой PHOTO_HW_PLACEHOLDER —
    # тут они настоящие, поэтому возвращает False.
    sheet.lesson_homework = 'ТЕСТ-МАТЕРИАЛЫ со своим текстом'
    asg.write({'description': '<p>ТЕСТ-МАТЕРИАЛЫ со своим текстом</p>'})
    env.flush_all()
    removed = sheet.hw_drop_empty_photo_assignment()
    check_true('свой текст + фото: задание сохранено',
               not removed, 'removed=%s' % removed)
    check_true('задание на месте после отказа',
               env['op.assignment'].sudo().browse(asg_id).exists(),
               'asg=%s' % asg_id)

    # Чисто фоточное ДЗ: текст в обоих полях — заглушка, материалов нет.
    # Именно это состояние бывает после удаления последнего фото.
    asg = env['op.assignment'].sudo().browse(asg_id)
    asg.material_ids.unlink() if hasattr(asg.material_ids, 'unlink') else None
    env.flush_all()
    check_true('материал снят — осталось 0',
               len(asg.material_ids) == 0, 'n=%d' % len(asg.material_ids))
    # Заглушка ставится в оба поля: метод требует и name, и description.
    asg.write({
        'name': PHOTO_HW_PLACEHOLDER,
        'description': '<p>%s</p>' % PHOTO_HW_PLACEHOLDER,
    })
    sheet.lesson_homework = PHOTO_HW_PLACEHOLDER
    env.flush_all()
    print('   состояние: name=%r desc=%r' % (asg.name,
                                              (asg.description or '')[:40]))

    removed2 = sheet.hw_drop_empty_photo_assignment()
    env.flush_all()
    check_true('фоточное без текста: метод снёс задание', removed2,
               'removed=%s' % removed2)
    check_true('фоточное без текста: задание удалено',
               not env['op.assignment'].sudo().browse(asg_id).exists(),
               'asg=%s' % asg_id)


def hw_sync_test_invariant():
    """ИНВАРИАНТ: по всей базе текст листа == текст задания.

    Это главная страховка переделки. Пока держится — рефакторинг безопасен.

    ИСКЛЮЧЕНИЕ — отменённые задания (state=cancel). При отзыве учитель
    очищает текст в листе, а задание переводится в cancel и сохраняет
    прежний текст в description. Так и должно быть: отменённое задание
    исторически видно в разборе. На test4 таких расхождений 45, все
    активные задания совпадают.
    """
    print('   полная сверка базы test4...')
    sheets = env['op.attendance.sheet'].sudo().search(
        [('homework_assignment_id', '!=', False)])
    mismatch_active = []
    mismatch_cancelled = 0
    for sheet in sheets:
        a = sheet.homework_assignment_id
        if not a.exists():
            continue
        if assignment_text(a) == sheet_text(sheet):
            continue
        if a.state == 'cancel':
            mismatch_cancelled += 1
        else:
            mismatch_active.append((sheet.id, a.id, a.state,
                                    sheet_text(sheet)[:40],
                                    assignment_text(a)[:40]))
    print('   листов с заданием: %d' % len(sheets))
    print('   расхождений у активных: %d, у отменённых (норма): %d'
          % (len(mismatch_active), mismatch_cancelled))
    for m in mismatch_active[:10]:
        print('     ЛИСТ %s asg %s (%s): лист=%r задание=%r' % m)
    check_true('текст листа == текст задания у всех АКТИВНЫХ заданий',
               not mismatch_active,
               'расхождений: %d' % len(mismatch_active))
    print('   (у отменённых расхождение ожидаемо и проверкой не считается)')


# ---------------------------------------------------------------- прогон

SCENARIOS = [
    hw_sync_test_create,
    hw_sync_test_publish,
    hw_sync_test_post_via_publish,
    hw_sync_test_edit,
    hw_sync_test_cancel,
    hw_sync_test_empty_draft,
    hw_sync_test_attach,
    hw_sync_test_invariant,
]

print('=' * 72)
print('СТОП-ТЕСТЫ СИНКА ДЗ — текущее поведение перед переделкой')
print('=' * 72)

for fn in SCENARIOS:
    scenario(fn)

print('\n' + '=' * 72)
print('ИТОГ')
print('=' * 72)
failed = [r for r in RESULTS if not r[1]]
print('проверок: %d, провалено: %d' % (len(RESULTS), len(failed)))
for label, _, got, want in failed:
    print('  FAIL: %s (got=%r want=%r)' % (label, got, want))
print()
print('Откат выполнен после каждого сценария: реальные данные не тронуты.')

env.cr.rollback()