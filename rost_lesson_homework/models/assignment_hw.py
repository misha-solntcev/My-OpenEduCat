from markupsafe import Markup

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class OpAssignment(models.Model):
    """Домашние задания: задание — единственный источник правды.

    Архитектура (согласована 2026-10-01, план
    .hermes/plans/2026-10-01_homework-architecture.md):

        задание (здесь)  — источник правды о тексте, сроке и флаге ответа
        лист урока       — черновик ввода, синхронизируется в эту сторону
        канал            — объявление, а не копия; post живёт один раз

    Пост в канале раньше искался поиском по тексту внутри тела сообщения
    (_hw_channel_find_message). Любая правка текста ДЗ делала такой поиск
    ненадёжным — это и было источником дублей у Ермаковой 10.09. Теперь пост
    хранится ссылкой hw_channel_message_id на конкретное сообщение: найти и
    переписать его можно однозначно, без разбора текста.

    Файл добавляет ТОЛЬКО методы и одно поле-хранение ссылки на сообщение.
    Никаких новых таблиц, никаких копий текста.
    """

    _inherit = 'op.assignment'

    # Ссылка на объявление в канале. Хранится, а не ищется по тексту:
    # один пост на одно задание, обновление и удаление — адресные.
    hw_channel_message_id = fields.Many2one(
        'mail.message', 'Объявление в канале',
        readonly=True, copy=False, index=True,
        help='Сообщение о ДЗ в канале класса/предмета. Создаётся один раз '
             'при выдаче; при правке текста перезаписывается, а не ищется '
             'заново по тексту.')

    # ------------------------------------------------------------------
    # Текст ДЗ: единственная точка записи
    # ------------------------------------------------------------------
    def hw_text(self):
        """Текст ДЗ как его видит ученик (description — HTML, снимаем).

        Переводы строк хранятся как <br/>, но html2plaintext их НЕ
        превращает обратно в \\n — вернул бы строку с текстом «<br/>» внутри.
        Разворачиваем сами: иначе текст не проходит round-trip (прочитал,
        записал, получил другой текст — и канал считал бы, что текст
        изменился, при каждом автосейве журнала.
        """
        self.ensure_one()
        from odoo.tools import html2plaintext
        plain = html2plaintext(self.description or '') or ''
        for br in ('<br/>', '<br />', '<br>', '<br />'):
            plain = plain.replace(br, '\n')
        return plain.replace('\r\n', '\n').strip()

    def hw_set_text(self, text):
        """Записать текст ДЗ в задание. Единственная точка записи.

        Пишет ОБА поля (name и description) — они хранят один и тот же
        текст в разных системах: name уходит в заголовок задания,
        description — в тело, откуда его читает миниапп ученика.

        description — HTML-поле, поэтому текст экранируется. Без этого
        «Прочитать "Садко" & выучить стр. 5-10» ломал разметку на '&', а
        попытка «починить» через striptags() съедала куски текста вроде
        «<стр. 5-10>», которые читались как тег.

        Возвращает True, если текст изменился.
        """
        self.ensure_one()
        text = (text or '').strip()
        old = self.hw_text()
        if old == text and (self.name or '').strip() == text:
            return False
        self.name = text
        # Переводы строк сохраняем: ДЗ бывает многострочным.
        safe = text.replace('\n', Markup('<br/>'))
        self.description = Markup('<p>%s</p>') % safe if text else False
        return True

    # ------------------------------------------------------------------
    # Объявление в канале: создать / обновить / убрать — адресно
    # ------------------------------------------------------------------
    def hw_channel(self, sheet):
        """Канал, где живёт объявление о ДЗ (у листа, без контекста)."""
        return sheet._hw_channel()

    def hw_post_to_channel(self, sheet, body=None):
        """Создать объявление о ДЗ в канале. Один раз, при выдаче.

        Ссылка на сообщение сохраняется в задании — дальше пост
        обновляется и удаляется адресно, без поиска по тексту.
        """
        self.ensure_one()
        channel = self.hw_channel(sheet)
        if not channel:
            return self.env['mail.message']
        if not body:
            body = self._hw_channel_body(sheet)
        try:
            with self.env.cr.savepoint():
                msg = channel.with_context(
                    mail_create_nosubscribe=True).message_post(
                        body=body,
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                        # Именно список id, а НЕ команды (4, id):
                        # mail_thread проверяет тип и падает с ValueError.
                        attachment_ids=[a.id for a in self.material_ids],
                    )
        except Exception:
            _logger.warning('Failed to post HW announcement to channel %s',
                            channel.id, exc_info=True)
            return self.env['mail.message']
        self.sudo().write({'hw_channel_message_id': msg.id})
        return msg

    def hw_update_channel_post(self, sheet, body=None):
        """Перезаписать объявление (текст ДЗ изменился после выдачи).

        Если ссылка есть — пишем по ней. Если ссылки нет (объявление
        создавалось до переделки, либо канал завели позже) — находим
        пост один раз по старому тексту и СРАЗУ сохраняем ссылку, чтобы
        больше к этому не возвращаться.
        """
        self.ensure_one()
        msg = self.hw_channel_message_id
        if not msg or not msg.exists():
            msg = sheet._hw_channel_find_legacy_message(self.hw_text())
            # Пост уже привязан к другому заданию — не забираем его. Иначе
            # при двух одинаковых текстах ДЗ в одном канале («Домашка» у
            # учителя — самое частое) правка одного переписала бы пост
            # другого. Тогда объявление считаем отсутствующим: ученик видит
            # актуальное ДЗ в миниаппе, а учитель может обновить вручную.
            if msg and msg.hw_assignment_ids and self not in msg.hw_assignment_ids:
                _logger.info(
                    'HW post %s already belongs to assignments %s, '
                    'not linking it to %s',
                    msg.id, msg.hw_assignment_ids.ids, self.id)
                return self.env['mail.message']
            if not msg:
                # Объявления не было — молча не создаём: ученик видит
                # актуальное ДЗ в миниаппе. Кнопка «Обновить в канале»
                # у учителя создаст его явно.
                return self.env['mail.message']
            self.sudo().write({'hw_channel_message_id': msg.id})
        if not body:
            body = self._hw_channel_body(sheet)
        try:
            with self.env.cr.savepoint():
                msg.write({
                    'body': body,
                    'attachment_ids': [(6, 0,
                                       [a.id for a in self.material_ids])],
                })
        except Exception:
            _logger.warning('Failed to update HW message %s in channel',
                            msg.id, exc_info=True)
        return msg

    def hw_drop_channel_post(self, sheet=None):
        """Убрать объявление: задание отозвали, снесли или очистили.

        По ссылке, если она есть; иначе — по тексту (объявление до
        переделки). После успеха ссылка чистится, чтобы повторный отзыв
        не искал заново.

        sheet необязателен: он нужен только для легаси-поиска, когда ссылки
        ещё нет. Сброс задания (hw_reset_clear) сносит пост по ссылке и
        листа под рукой может не быть.
        """
        self.ensure_one()
        msg = self.hw_channel_message_id
        if not msg or not msg.exists():
            if not sheet:
                return False
            msg = sheet._hw_channel_find_legacy_message(self.hw_text())
        if not msg:
            return False
        try:
            with self.env.cr.savepoint():
                self.env['mail.message'].sudo().browse(msg.id).unlink()
        except Exception:
            _logger.warning('Failed to delete HW message %s from channel',
                            msg.id, exc_info=True)
            return False
        self.sudo().write({'hw_channel_message_id': False})
        return True

    def _hw_channel_body(self, sheet):
        """Текст объявления. Собирается из задания — источника правды."""
        self.ensure_one()
        deadline = self.submission_date
        return Markup(
            '<b>Новое домашнее задание</b> (%(subject)s)<br/>%(hw)s<br/>'
            'Срок сдачи: %(deadline)s'
        ) % {
            'subject': sheet.subject_id.name,
            'hw': self.name or '',
            'deadline': deadline.strftime('%d.%m.%Y %H:%M')
            if deadline else '—',
        }