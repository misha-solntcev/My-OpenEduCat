from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

import logging

_logger = logging.getLogger(__name__)

# Текст-заглушка, когда ДЗ = только фото (учитель не писал описание).
# Живёт в имени и описании задания, поэтому по нему же узнаём фоточное
# ДЗ при удалении последнего материала. Такая же константа есть в
# rost_max_miniapp/controllers/timetable.py: модули НЕ зависят друг от
# друга, импортировать нельзя — при правке меняй оба места.
PHOTO_HW_PLACEHOLDER = 'Домашнее задание (фото)'


class OpAttendanceSheet(models.Model):
    _inherit = 'op.attendance.sheet'

    lesson_homework = fields.Char('Домашнее задание', size=512)
    homework_assignment_id = fields.Many2one(
        'op.assignment', 'ДЗ (op.assignment)', readonly=True, copy=False)
    # Материалы задания (вложения учителя) — editable related на задание:
    # запись с формы журнала прозрачно уходит в op.assignment.material_ids.
    # Виджет many2many_binary вью требует записи — см. views/.
    material_ids = fields.Many2many(
        'ir.attachment', string='Материалы задания',
        related='homework_assignment_id.material_ids', readonly=False)

    # ------------------------------------------------------------------
    # Срок сдачи: следующий урок того же предмета у того же batch
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Дублирование ДЗ в канал класса/предмета (Discuss)
    # ------------------------------------------------------------------
    def _hw_channel(self):
        """Канал предмета «<batch> — <subject>», фолбэк — канал класса «<batch>»."""
        self.ensure_one()
        Channel = self.env['discuss.channel'].sudo()
        names = []
        if self.batch_id and self.subject_id:
            names.append(f"{self.batch_id.name} — {self.subject_id.name}")
        if self.batch_id:
            names.append(self.batch_id.name)
        for name in names:
            ch = Channel.search([
                ('name', '=', name),
                ('channel_type', '=', 'channel'),
            ], limit=1)
            if ch:
                return ch
        return Channel.browse(())

    def _hw_channel_post(self, asg, body, attachments=None):
        """Пост в канал от текущего юзера. Безопасно: любая ошибка — только warning."""
        self.ensure_one()
        channel = self._hw_channel()
        if not channel:
            return
        try:
            with self.env.cr.savepoint():
                channel.with_context(mail_create_nosubscribe=True).message_post(
                    body=body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    # Именно список id, а НЕ команды (4, id): mail_thread
                    # проверяет тип и падает с ValueError «вложения должны
                    # передаваться в виде списка ID». Этим молча гасилось
                    # объявление в канал — ошибка ловилась только в логе.
                    attachment_ids=[a.id for a in (attachments or [])],
                )
        except Exception:
            _logger.warning(
                'Failed to post HW announcement to channel %s',
                channel.id,
                exc_info=True,
            )

    def _hw_channel_announce(self, asg, event, attachments=None, find_needle=None):
        if self.env.context.get('hw_skip_channel_announce'):
            return
        self.ensure_one()
        deadline = asg.submission_date
        body = Markup(
            '<b>Новое домашнее задание</b> (%(subject)s)<br/>%(hw)s<br/>'
            'Срок сдачи: %(deadline)s'
        ) % {
            'subject': self.subject_id.name,
            'hw': asg.name,
            'deadline': deadline.strftime('%d.%m.%Y %H:%M') if deadline else '—',
        }
        if event == 'created':
            self._hw_channel_post(asg, body, attachments=attachments)
        else:  # 'edited' — перезаписать исходное сообщение (Odoo сам пометит
            # «(изменено)»), а не плодить новые посты. Ищем по find_needle
            # (старый текст ДЗ): в теле сообщения текст ещё старый.
            msg = self._hw_channel_find_message(find_needle or asg.name)
            if msg:
                try:
                    with self.env.cr.savepoint():
                        msg.write({
                            'body': body,
                            'attachment_ids': [(6, 0, [
                                a.id for a in (attachments or [])])],
                        })
                except Exception:
                    _logger.warning(
                        'Failed to update HW message %s in channel',
                        msg.id,
                        exc_info=True,
                    )
            # Сообщения нет (создавали до включения дубля в канал) — молча
            # не восстанавливаем: ученик видит актуальное ДЗ в миниаппе.

    def hw_drop_empty_photo_assignment(self):
        """Удалён последний материал ФОТОЧНОГО ДЗ (текст = заглушка) —
        задание стало пустым мусором. Сносим и задание, и заглушку на
        уроке; выданное (publish/finish) ещё и отменяем с удалением поста
        в канале.

        Возвращает True, если задание было снесено. Собственный текст
        учителя (не заглушка) НЕ трогаем: удаление фото не отменяет ДЗ,
        у которого есть описание. Правило живёт в модели, а не в
        контроллере, — иначе его нечем проверить без HTTP-сессии.
        """
        self.ensure_one()
        asg = self.homework_assignment_id
        if not asg or asg.material_ids:
            return False
        if (asg.name or '').strip() != PHOTO_HW_PLACEHOLDER:
            return False
        # description хранится как HTML («<p>…</p>»), сравнивать с голым
        # текстом нельзя — снимаем разметку. Сверяем оба поля, чтобы не
        # снести ДЗ, которому учитель потом написал описание.
        desc = (html2plaintext(asg.description or '') or '').strip()
        if desc != PHOTO_HW_PLACEHOLDER:
            return False
        # hw_skip_sync: синк отработает по пустому тексту сам, второй раз
        # запускать незачем.
        self.with_context(hw_skip_sync=True).write({'lesson_homework': False})
        if asg.state in ('publish', 'finish'):
            asg.act_cancel()
            self._hw_channel_delete(asg)
        self.homework_assignment_id = False
        asg.unlink()
        return True

    def _next_lesson_datetime(self):
        self.ensure_one()
        now = fields.Datetime.now()
        nxt = self.env['op.session'].sudo().search([
            ('faculty_id', '=', self.session_id.faculty_id.id),
            ('subject_id', '=', self.subject_id.id),
            ('batch_id', '=', self.batch_id.id),
            ('start_datetime', '>', max(self.start_datetime, now)),
            ('state', '!=', 'cancel'),
        ], order='start_datetime asc', limit=1)
        return nxt.start_datetime if nxt else (
            now + timedelta(days=7))

    # ------------------------------------------------------------------
    # Авто-создание op.assignment при завершении урока
    # ------------------------------------------------------------------
    def _homework_sync(self):
        for sheet in self:
            # ДЗ можно выдать до начала урока и после завершения.
            # Черновики и отменённые журналы не синхронизируем.
            if sheet.state not in ('done', 'start', 'confirm'):
                continue
            hw = (sheet.lesson_homework or '').strip()
            asg = sheet.homework_assignment_id

            if not hw:
                # ДЗ убрали из журнала. Различаем два случая:
                #  - задание было выдано (publish/finish) — это «отозвали»,
                #    переводим в cancel и убираем пост из канала;
                #  - задание было черновиком — публикации не было, отменять
                #    нечего и нечего показывать в разборе данных, удаляем.
                #    Иначе sync на следующем confirm воскресит его обратно.
                if asg and asg.state not in ('cancel', 'finish') \
                        and not asg.material_ids:
                    if asg.state == 'draft':
                        sheet.homework_assignment_id = False
                        asg.unlink()
                    else:
                        asg.act_cancel()
                        sheet._hw_channel_delete(asg)
                continue

            if asg:
                # Обновляем текст существующего задания. Сравнение нормализованное:
                # lesson_homework (Char) и description (Text) расходятся хвостовыми
                # переводами строки -> иначе каждое сохранение журнала постит
                # «изменён» в канал (пачки дублей у Ермаковой 10.09).
                old_hw = (asg.description or '').strip()
                text_changed = old_hw != hw
                if (asg.grading_assignment_id.name or '').strip() != hw:
                    asg.grading_assignment_id.name = hw
                if text_changed:
                    asg.description = hw
                if asg.state == 'cancel':
                    # Задание заново ввели после отзыва. Возвращаем в
                    # черновик, а не сразу в publish: текст учитель мог
                    # начать править, выдача — явной кнопкой «Выдать».
                    asg.act_set_to_draft()
                elif asg.state == 'draft':
                    # Черновик ещё не выдан — поста в канале нет, правим
                    # текст молча. Иначе каждое сохранение журнала плодило
                    # бы «изменено» в канале у задания, которое никто не видел.
                    pass
                elif text_changed:
                    # Текст правлен — перезаписываем исходное сообщение в канале.
                    # Odoo сам пометит его «(изменено)». Новые посты не плодим.
                    # Ищем по СТАРОМУ тексту: в теле сообщения он ещё старый.
                    sheet._hw_channel_announce(
                        asg, 'edited',
                        attachments=asg.material_ids,
                        find_needle=old_hw)
                continue

            # Создаём новое задание — в черновике.
            # Публикует его учитель явной кнопкой «Выдать» (hw_publish),
            # а не автосинк: пустой автосейв на confirm/done больше не
            # роняет ученикам «Домашнее задание (фото)». Срок и пост в
            # канал считаются в момент публикации, а не создания.
            atype = self.env['grading.assignment.type'].search([
                ('name', 'ilike', 'Домашнее задание')], limit=1)
            if not atype:
                raise UserError(
                    'Не найден тип задания «Домашнее задание». '
                    'Создайте его в модуле Задания.')
            sheet.homework_assignment_id = self.env['op.assignment'].create({
                'name': hw,
                'answer_required': sheet.homework_answer_required,
                'course_id': sheet.course_id.id,
                'subject_id': sheet.subject_id.id,
                'faculty_id': (sheet.faculty_id or sheet.session_id.faculty_id).id,
                'assignment_type': atype.id,
                'issued_date': fields.Datetime.now(),
                # Срок у черновика не «окончательный», но submission_date
                # NOT NULL в БД — без значения задание не создаётся.
                # Поэтому ставим сразу, а в момент публикации («Выдать»)
                # пересчитываем от момента выдачи.
                'submission_date': sheet._next_lesson_datetime(),
                'description': hw,
                'batch_id': sheet.batch_id.id,
                'state': 'draft',
                'allocation_ids': [
                    (6, 0, self.env['op.student'].search([
                        ('active_batch_id', '=', sheet.batch_id.id),
                        ('state', '=', 'studying'),
                    ]).ids)],
            })

    def _hw_channel_find_message(self, needle_text):
        """Исходное сообщение о ДЗ в канале — тело содержит текст задания."""
        self.ensure_one()
        channel = self._hw_channel()
        if not channel:
            return self.env['mail.message'].browse(())
        needle = (html2plaintext(needle_text or '') or '').strip()[:100]
        if not needle:
            return self.env['mail.message'].browse(())
        msg = self.env['mail.message'].sudo().search([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', channel.id),
            ('body', 'ilike', needle),
            ('message_type', '=', 'comment'),
        ], order='id asc', limit=1)
        return msg

    def _hw_channel_delete(self, asg):
        """ДЗ очистили — удалить сообщение в канале (отменённое ДЗ не постим)."""
        self.ensure_one()
        channel = self._hw_channel()
        if not channel:
            return
        needle = (html2plaintext(asg.name or '') or '').strip()[:100]
        if not needle:
            return
        msg = self.env['mail.message'].sudo().search([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', channel.id),
            ('body', 'ilike', needle),
            ('message_type', '=', 'comment'),
        ], order='id desc', limit=1)
        if msg:
            try:
                with self.env.cr.savepoint():
                    self.env['mail.message'].sudo().browse(msg.id).unlink()
            except Exception:
                _logger.warning(
                    'Failed to delete HW message %s from channel',
                    msg.id,
                    exc_info=True,
                )

    def write(self, vals):
        res = super().write(vals)
        # hw_skip_sync: контроллер сам разберётся с заданием (удаление
        # черновика). Без этой проверки sync на lesson_homework='' создал бы
        # задание заново на том же write.
        if self.env.context.get('hw_skip_sync'):
            return res
        if 'lesson_homework' in vals or 'state' in vals:
            self._homework_sync()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        sheets = super().create(vals_list)
        sheets._homework_sync()
        return sheets
