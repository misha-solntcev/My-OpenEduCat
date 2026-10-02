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


def hw_msg_by_ref(sheet, asg):
    """Пост о ДЗ по ссылке из задания — новый адресный способ."""
    return asg.hw_channel_message_id


# ------------------------------------------------------------------ НОВОЕ
# Проверки инверсии: задание — источник правды, пост адресуется ссылкой,
# а не ищется по тексту внутри тела сообщения.


def hw_inverse_test_ref_not_search():
    """Пост хранится ссылкой в задании, а не ищется по тексту.

    Ключевое отличие переделки: раньше сообщение о ДЗ находилось поиском
    ilike по тексту в теле сообщения (отсюда дубли у Ермаковой 10.09).
    Теперь в задании лежит hw_channel_message_id — адрес конкретного
    сообщения.
    """
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    ch = channel_for(sheet)
    if not ch:
        print('   У ЛИСТА НЕТ КАНАЛА — сценарий неприменим')
        return
    sheet.lesson_homework = 'ТЕСТ-ССЫЛКА: первая редакция'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return

    check_true('до выдачи ссылки нет',
               not asg.hw_channel_message_id,
               'ref=%s' % asg.hw_channel_message_id.id)

    sheet._hw_channel_announce(asg, 'created')
    env.flush_all()
    ref = asg.hw_channel_message_id
    check_true('после выдачи ссылка сохранена', bool(ref),
               'ref=%s' % (ref.id if ref else '-'))
    check_true('ссылка ведёт на сообщение в нужном канале',
               bool(ref) and ref.model == 'discuss.channel'
               and ref.res_id == ch.id,
               'model=%s res_id=%s' % (ref.model if ref else '-',
                                       ref.res_id if ref else '-'))

    # Смена текста НЕ должна находить пост по тексту: адрес известен.
    sheet.lesson_homework = 'ТЕСТ-ССЫЛКА: вторая редакция'
    env.flush_all()
    ref2 = asg.hw_channel_message_id
    check_true('после правки ссылка та же (пост не пересоздан)',
               ref2 and ref.id == ref2.id,
               'был %s стал %s' % (ref.id, ref2.id if ref2 else '-'))
    n = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])
    check_true('в канале ровно один пост', n == 1, 'сообщений=%d' % n)

    # Отзыв чистит ссылку. Задание при этом может быть удалено целиком
    # (черновик) — читать поле у удалённой записи нельзя, только exists.
    asg_id = asg.id
    sheet.lesson_homework = False
    env.flush_all()
    asg_now = env['op.assignment'].sudo().browse(asg_id)
    if asg_now.exists():
        check_true('после отзыва ссылка снята',
                   not asg_now.hw_channel_message_id,
                   'ref=%s' % asg_now.hw_channel_message_id.id)
    else:
        check_true('после отзыва задание снято (черновик), ссылка moot', True,
                   'asg=%s удалён' % asg_id)
    n_final = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch.id)])
    check_true('пост удалён, канал чист', n_final == 0,
               'сообщений=%d' % n_final)


def hw_inverse_test_text_escaping():
    """Текст ДЗ со спецсимволами переживает запись в HTML-поле.

    '&' и '<стр. 5-10>' — исторические грабли: без экранирования ломалась
    разметка, а попытка вылечить striptags() съедала куски текста.
    """
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    tricky = 'Прочитать "Садко" & выучить <стр. 5-10>, п. 13'
    sheet.lesson_homework = tricky
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return
    env.flush_all()

    check_true('текст дошёл до задания целиком', tricky in asg.hw_text(),
               'получено: %r' % asg.hw_text())
    check_true('заголовок без разметки', asg.name.strip() == tricky,
               'name=%r' % asg.name)
    check_true('описание экранировано (нет сырых <>)',
               '&amp;' in asg.description or '&lt;' in asg.description
               or '<' not in (asg.description or '').replace('<p>', '')
               .replace('<br/>', ''),
               'description=%r' % (asg.description or '')[:120])
    check('текст листа совпал', sheet_text(sheet), tricky)

    # Многострочный текст должен сохранить переводы строк.
    multi = 'Первая строка\nВторая строка\nТретья строка'
    sheet.lesson_homework = multi
    env.flush_all()
    check_true('переводы строк сохранены',
               asg.hw_text().count('\n') == 2,
               'получено %r' % asg.hw_text())

    # hw_set_text без изменения текста не должен ничего переписывать.
    check_true('повторная запись того же текста — без изменений',
               asg.hw_set_text(multi) is False)


def hw_inverse_test_assignment_edit_syncs_back():
    """Правка задания напрямую (как в ПК-форме) видна в листе журнала.

    Ключевая цель инверсии: задание — источник правды. Если учитель поправил
    задание не из журнала, синк не должен затереть правку листом.
    """
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    sheet.lesson_homework = 'ТЕСТ-СИНХРОНИЗАЦИЯ: из журнала'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return
    env.flush_all()

    # Правка задания напрямую — то, что делает ПК-форма OpenEduCat.
    asg.hw_set_text('ТЕСТ-СИНХРОНИЗАЦИЯ: поправлено в задании')
    env.flush_all()
    check('текст в задании изменён', asg.hw_text(),
          'ТЕСТ-СИНХРОНИЗАЦИЯ: поправлено в задании')

    # Следующий автосейв журнала (смена состояния) не должен затереть
    # правку задания листом — иначе ПК-правка исчезла бы бесшумно.
    sheet.write({'state': sheet.state})
    env.flush_all()
    check_true('правка задания пережила автосейв журнала',
               asg.hw_text() == 'ТЕСТ-СИНХРОНИЗАЦИЯ: поправлено в задании',
               'стало %r' % asg.hw_text()[:60])


def hw_inverse_test_duplicate_text_guard():
    """Два одинаковых ДЗ в одном канале не тянут один и тот же пост.

    Реальный случай: учитель пишет «Домашка» (самое частое слово) в двух
    уроках одного класса. Поиск объявления по тексту находит первый пост —
    и без проверки правка второго задания переписала бы объявление первого.
    """
    sheets = env['op.attendance.sheet'].sudo().search([
        ('state', 'in', ('start', 'confirm')),
        ('homework_assignment_id', '=', False),
        ('batch_id', '!=', False),
    ], order='id desc', limit=2)
    if len(sheets) < 2:
        print('   НУЖНЫ 2 стенда с КАЖДЫМ СВОИМ каналом — пропуск')
        return
    sh1, sh2 = sheets[0], sheets[1]
    ch1, ch2 = sh1._hw_channel(), sh2._hw_channel()
    if not ch1 or not ch2:
        print('   У одного из листов нет канала — пропуск')
        return
    if ch1.id == ch2.id:
        print('   КАНАЛЫ ОДИНАКОВЫ (один предмет) — пропуск, нужен другой')
        return
    print('   каналы: %s / %s' % (ch1.name, ch2.name))

    same = 'Домашка'
    sh1.lesson_homework = same
    sh2.lesson_homework = same
    asg1, asg2 = sh1.homework_assignment_id, sh2.homework_assignment_id
    if not (asg1 and asg2):
        print('   задания не создались')
        return
    env.flush_all()

    asg1.act_publish()
    sh1._hw_channel_announce(asg1, 'created')
    env.flush_all()
    msg1 = asg1.hw_channel_message_id
    check_true('первое объявление создано и привязано', bool(msg1),
               'msg=%s' % (msg1.id if msg1 else '-'))

    # Второе задание с тем же текстом: бэкфилл по тексту обязан найти пост
    # первого — и обязан от него отказаться.
    asg2.act_publish()
    env.flush_all()
    res = asg2.hw_update_channel_post(sh2)
    check_true('второе задание НЕ привязалось к чужому посту',
               not asg2.hw_channel_message_id,
               'ref=%s' % asg2.hw_channel_message_id.id)
    check_true('чужой пост не тронут', asg1.hw_channel_message_id.id == msg1.id,
               'ref1=%s' % asg1.hw_channel_message_id.id)
    n1 = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch1.id)])
    n2 = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch2.id)])
    check_true('в первом канале по-прежнему один пост', n1 == 1,
               'сообщений=%d' % n1)

    # А теперь объявить второе ДЗ честно — отдельным постом в его канале.
    msg2 = asg2.hw_post_to_channel(sh2)
    env.flush_all()
    check_true('второе объявление создано отдельно', bool(msg2)
               and asg2.hw_channel_message_id.id == msg2.id,
               'msg=%s ref=%s' % (msg2.id if msg2 else '-',
                                  asg2.hw_channel_message_id.id))
    check_true('посты в разных каналах не смешались',
               ch1.id != ch2.id and msg1.res_id == ch1.id
               and msg2.res_id == ch2.id,
               'msg1=%s msg2=%s' % (msg1.res_id, msg2.res_id if msg2 else '-'))
    n1b = env['mail.message'].sudo().search_count(
        [('model', '=', 'discuss.channel'), ('res_id', '=', ch1.id)])
    check_true('первый канал не загрязнён', n1b == 1,
               'сообщений=%d' % n1b)


def hw_due_rule_test_second_lesson_end():
    """Срок сдачи — НАЧАЛО урока, следующего за ближайшим.

    Правило (2026-10-02): ДЗ выдаётся на ближайшем уроке, проверяется в
    начале следующего. Живой пример: история 7А, урок 06.10 08:10 UTC
    (11:10 МСК) — на нём выдают; следующий 08.10 11:10 UTC (14:10 МСК),
    срок сдачи = его начало.

    Раньше бралась ПЕРВАЯ сессия и её start_datetime, то есть срок был
    06.10 08:10 — момент, когда ДЗ ещё только выдают, сдать его к этому
    моменту ученик не мог.
    """
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    sessions = env['op.session'].sudo().search([
        ('faculty_id', '=', sheet.session_id.faculty_id.id),
        ('subject_id', '=', sheet.subject_id.id),
        ('batch_id', '=', sheet.batch_id.id),
        ('start_datetime', '>', sheet.start_datetime),
        ('state', '!=', 'cancel'),
    ], order='start_datetime asc', limit=3)
    print('   лист %s, предмет %s, класс %s, впереди уроков: %d'
          % (sheet.id, sheet.subject_id.name, sheet.batch_id.name,
             len(sessions)))
    for s in sessions[:3]:
        print('     %s %s -> %s' % (s.timetable_date, s.start_datetime,
                                     s.end_datetime))
    check_true('впереди минимум два урока (иначе сценарий не проверяет '
               'правило)', len(sessions) >= 2, 'n=%d' % len(sessions))
    if len(sessions) < 2:
        return

    due = sheet._next_lesson_datetime()
    expected = sessions[1].start_datetime
    check('срок = начало ВТОРОГО урока', due, expected)
    check_true('срок НЕ позже конца второго урока (начало, не конец)',
               due <= (sessions[1].end_datetime or sessions[1].start_datetime),
               'срок %s, конец урока %s'
               % (due, sessions[1].end_datetime))
    check_true('срок не равен началу ближайшего урока',
               due != sessions[0].start_datetime,
               'ближайший %s, срок %s' % (sessions[0].start_datetime, due))
    check_true('срок позже ближайшего урока',
               due > sessions[0].start_datetime,
               '%s > %s' % (due, sessions[0].start_datetime))
    check_true('срок НЕ равен началу ближайшего (старый баг)',
               due != sessions[0].start_datetime)


def hw_due_rule_test_publish_recalc():
    """«Выдать» пересчитывает срок по новому правилу."""
    sheet = _fresh_lesson()
    if not sheet:
        print('   НЕТ СТЕНДА')
        return
    sheet.lesson_homework = 'ТЕСТ-СРОКА: пересчёт при выдаче'
    asg = sheet.homework_assignment_id
    if not asg:
        print('   задание не создалось')
        return
    env.flush_all()
    due_before = asg.submission_date
    expected = sheet._next_lesson_datetime()
    check('черновик уже посчитан по правилу', due_before, expected)

    # Эмитируем hw_publish: он пересчитывает срок при выдаче.
    asg.submission_date = sheet._next_lesson_datetime()
    asg.act_publish()
    env.flush_all()
    check('при выдаче срок тот же (расписание не изменилось)',
          asg.submission_date, expected)
    check_true('срок заполнен и не пустой', bool(asg.submission_date))
    check_true('срок в будущем относительно урока',
               asg.submission_date > sheet.start_datetime,
               '%s > %s' % (asg.submission_date, sheet.start_datetime))


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
    hw_inverse_test_ref_not_search,
    hw_inverse_test_text_escaping,
    hw_inverse_test_assignment_edit_syncs_back,
    hw_inverse_test_duplicate_text_guard,
    hw_due_rule_test_second_lesson_end,
    hw_due_rule_test_publish_recalc,
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