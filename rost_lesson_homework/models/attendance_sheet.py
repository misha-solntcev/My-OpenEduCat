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


def sheet_text(sheet):
    """Текст ДЗ в листе журнала — как черновик ввода, без разметки."""
    return (sheet.lesson_homework or '').strip()


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
    # Статус ДЗ текущего урока: по нему баннер «не выдано» и кнопка
    # «Выдать» решают, показываться ли (см. views/attendance_sheet_homework_view.xml).
    homework_state = fields.Selection(
        related='homework_assignment_id.state', readonly=True)

    def hw_publish_sheet(self):
        """Выдать ДЗ текущего урока прямо из журнала.

        Тот же hw_publish, что кнопка «Выдать» в форме задания
        (models/assignment_hw_publish.py): срок пересчитан, задание
        опубликовано, объявление ушло в канал. Разница только в месте
        вызова: учитель не должен уходить из журнала, чтобы выдать ДЗ.
        Пустое ДЗ — ошибка: случайный клик не публикует мусор.
        """
        self.ensure_one()
        asg = self.homework_assignment_id
        if not asg:
            raise UserError(
                'Сначала впишите домашнее задание и сохраните журнал.')
        res = asg.hw_publish()
        if res.get('posted'):
            message = 'ДЗ выдано, объявление отправлено в канал класса'
            ntype = 'success'
        else:
            message = ('Задание выдано, но канал класса не найден — '
                       'объявление не отправлено')
            ntype = 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': ntype,
                'message': message,
                'details': 'Срок сдачи: %s' % (
                    self.homework_assignment_id.submission_date.strftime(
                        '%d.%m.%Y %H:%M')
                    if self.homework_assignment_id.submission_date else '—'),
                'sticky': False,
                'next': {'type': 'reload'},
            },
        }

    # ------------------------------------------------------------------
    # Срок сдачи: следующий урок того же предмета у того же batch
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

    def _hw_channel_announce(self, asg, event, attachments=None,
                             find_needle=None):
        """Объявление о ДЗ в канале.

        Тонкая обёртка над методами задания (models/assignment_hw.py):
        текст берётся из задания, а сообщение адресуется по ссылке
        hw_channel_message_id, а не ищется по тексту.

        find_needle оставлен параметром только для совместимости вызовов и
        НЕ используется: поиск по тексту в теле сообщения и был причиной
        дублей объявлений. Если ссылка есть — пишем по ней.
        """
        if self.env.context.get('hw_skip_channel_announce'):
            return
        self.ensure_one()
        if not hasattr(asg, 'hw_post_to_channel'):
            return
        if event == 'created':
            return asg.hw_post_to_channel(self)
        # 'edited' — перезаписать исходное сообщение (Odoo сам пометит
        # «(изменено)»), а не плодить новые посты.
        return asg.hw_update_channel_post(self)

    def _hw_channel_find_legacy_message(self, needle_text):
        """Объявление о ДЗ, созданное ДО переделки — поиск по тексту.

        Работает только для старых сообщений, у которых ещё нет ссылки
        hw_channel_message_id. Найденное сразу сохраняется в задании, и
        дальше поиск по тексту не повторяется.
        """
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

    # Историческое имя. Оставлено, потому что на него ссылаются тесты и
    # он читает понятнее в местах, где ищут именно «сообщение о ДЗ».
    _hw_channel_find_message = _hw_channel_find_legacy_message

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
            asg.hw_drop_channel_post(self)
        self.homework_assignment_id = False
        asg.unlink()
        return True

    def _next_lesson_datetime(self):
        """Срок сдачи ДЗ: НАЧАЛО урока, следующего за ближайшим.

        Правило (согласовано 2026-10-02): ДЗ выдаётся на ближайшем уроке,
        а проверяется в начале следующего — учитель в начале урока уже
        разбирает домашнее. Поэтому срок = начало ВТОРОГО урока, а не его
        конец.

        Пример: история 7А. Урок 06.10 11:10 МСК — на нём задание выдают.
        Следующий 08.10 14:10 МСК, срок сдачи — его начало.

        Раньше бралась ПЕРВАЯ сессия: срок совпадал с началом урока, на
        котором ДЗ ещё только выдают, — сдать его к этому моменту ученик
        физически не мог.

        Крайние случаи:
        - сессий нет — плюс неделя, как раньше;
        - сессия одна — срок = её начало, лучше, чем пусто: учитель увидит
          в карточке и поправит руками.
        """
        self.ensure_one()
        now = fields.Datetime.now()
        sessions = self.env['op.session'].sudo().search([
            ('faculty_id', '=', self.session_id.faculty_id.id),
            ('subject_id', '=', self.subject_id.id),
            ('batch_id', '=', self.batch_id.id),
            ('start_datetime', '>', max(self.start_datetime, now)),
            ('state', '!=', 'cancel'),
        ], order='start_datetime asc', limit=2)
        # Один урок впереди — срок на него, а не через два.
        return sessions[-1].start_datetime if sessions else (
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
                        # Объявление могло уже быть создано (например,
                        # учитель залил фото и нажал «Выдать», потом вернул
                        # задание в черновик). Без этой строки пост остался
                        # бы в канале навсегда — снос задания не отменяет
                        # уже сказанное ученикам.
                        asg.hw_drop_channel_post(sheet)
                        asg.unlink()
                    else:
                        asg.act_cancel()
                        asg.hw_drop_channel_post(sheet)
                continue

            if asg:
                # Инверсия хранилища. Источник правды — задание.
                #
                # Что означает текущий write листа:
                #   hw_hw_pulled=False — учитель ПРАВИТ текст в журнале,
                #     его воля побеждает, пишем в задание;
                #   hw_hw_pulled=True — текст в листе не трогали, это
                #     автосейв по смене состояния урока. Тогда источник
                #     правды — задание, и лист подтягивает его текст
                #     (учитель мог поправить ДЗ из ПК-формы OpenEduCat
                #     или из карточки ДЗ в миниаппе — тирать это листом
                #     было бы тихой потерей правки).
                pulled = self.env.context.get('hw_hw_pulled')
                if pulled:
                    # Лист НЕ диктует текст. Обновляем его из задания.
                    asg_text = asg.hw_text()
                    if sheet_text(sheet) != asg_text:
                        sheet.with_context(hw_skip_sync=True).write(
                            {'lesson_homework': asg_text or False})
                    continue
                text_changed = asg.hw_set_text(hw)
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
                    # Текст правлен — перезаписываем исходное сообщение в
                    # канале по ссылке из задания (адресно, не по тексту).
                    sheet._hw_channel_announce(asg, 'edited')
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
            asg = self.env['op.assignment'].create({
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
                # description — HTML-поле и required: заполняем сразу
                # экранированным текстом, иначе создание упадёт на '&'.
                'description': (Markup('<p>%s</p>')
                                % hw.replace('\n', Markup('<br/>'))),
                'batch_id': sheet.batch_id.id,
                'state': 'draft',
                'allocation_ids': [
                    (6, 0, self.env['op.student'].search([
                        ('active_batch_id', '=', sheet.batch_id.id),
                        ('state', '=', 'studying'),
                    ]).ids)],
            })
            # Создание — тоже через единственную точку записи текста:
            # name и description обязаны совпадать с первого момента.
            asg.hw_set_text(hw)
            sheet.homework_assignment_id = asg

    def write(self, vals):
        res = super().write(vals)
        # hw_skip_sync: контроллер сам разберётся с заданием (удаление
        # черновика). Без этой проверки sync на lesson_homework='' создал бы
        # задание заново на том же write.
        if self.env.context.get('hw_skip_sync'):
            return res
        if 'lesson_homework' in vals:
            # Учитель правит текст ДЗ в журнале — это его воля, задание
            # получает этот текст (hw_hw_pulled не выставлен).
            self._homework_sync()
        elif 'state' in vals:
            # Автосейв по смене состояния урока (начали/завершили).
            # Текст в листе тут ни при чём: ДЗ могли поправить в ПК-форме
            # или в карточке ДЗ миниаппа. Поэтому источник правды —
            # задание, и лист подтягивает его текст, а не наоборот.
            self.with_context(hw_hw_pulled=True)._homework_sync()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        sheets = super().create(vals_list)
        sheets._homework_sync()
        return sheets
