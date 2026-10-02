# -*- coding: utf-8 -*-
"""Выдача домашнего задания — серверное действие (ПК + миниапп).

Зачем (2026-10-02, вариант П1). Публикация ДЗ жила только в контроллере
миниаппа: api_lesson_hw_publish. Кнопка Publish в ПК-форме — это act_publish
из openeducat_assignment, который меняет ТОЛЬКО state. То есть учитель,
нажавший «Publish» в браузере, получал задание без объявления в канале и без
срока, посчитанного по урокам. Ученики ничего не видели, а срок стоял
прошлый. Пока ДЗ было только в миниаппе, это не мешало; теперь раздел
«Задания» — рабочее место, и ПК обязан вести себя так же.

Здесь — единственная реализация выдачи. Миниапп вызывает её вместо своей
логики (правка в контроллере — отдельным шагом), ПК вызывает её из кнопки.
Оба получают одинаковый результат: срок посчитан, задание опубликовано,
объявление в канале создано один раз.

Правило срока — _next_lesson_datetime на листе урока: начало урока,
следующего за ближайшим (ДЗ выдаётся на ближайшем, проверяется в начале
следующего). Если листа нет — задание создано в ПК-форме, срок ставил
учитель руками, пересчитывать по расписанию нельзя, и действие его не
трогает.

Объявление в канал постится только при выдаче. Повторный вызов на
publish/finish — успех без действий: кнопка может оказаться нажатой дважды.
"""

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OpAssignmentPublish(models.Model):
    _inherit = 'op.assignment'

    # Обратная ссылка на урок, из которого задание выдано. В ПК её не было:
    # из листа журнала связь шла вниз (homework_assignment_id), а обратно
    # вернуться в урок было нельзя. Считаем, а не храним, — лист и так
    # смотрит на задание.
    hw_sheet_id = fields.Many2one(
        'op.attendance.sheet', compute='_compute_hw_sheet_id',
        string='Урок', help='Урок, на котором задание было выдано.')

    # Счётчика «К проверке» нет намеренно: в ПК уже есть кнопка
    # «Ответы на задания» (get_assignment_submissions), которая открывает
    # все сдачи задания и работает. Вторая кнопка на то же самое только
    # путает учителя.

    def _compute_hw_sheet_id(self):
        sheets = self.env['op.attendance.sheet'].sudo().search(
            [('homework_assignment_id', 'in', self.ids)])
        by_asg = {}
        for sheet in sheets:
            by_asg.setdefault(sheet.homework_assignment_id.id, sheet)
        for asg in self:
            asg.hw_sheet_id = by_asg.get(asg.id)

    def hw_publish(self):
        """Выдать задание: срок, публикация, объявление в канале.

        Идемпотентно. Возвращает словарь с результатом, чтобы вызывающий
        (кнопка ПК или контроллер миниаппа) показал, что произошло.
        """
        self.ensure_one()
        if self.state in ('publish', 'finish'):
            return {'success': True, 'state': self.state,
                    'posted': False, 'recomputed': False,
                    'message': _('Задание уже выдано')}
        if self.state == 'cancel':
            raise UserError(
                _('Задание отозвано — впишите текст заново'))

        sheet = self.env['op.attendance.sheet'].sudo().search(
            [('homework_assignment_id', '=', self.id)], limit=1)

        # Срок пересчитываем ВСЕГДА, а не только при пустом: черновик мог
        # провисеть несколько дней, и «следующий урок» от момента создания
        # уже прошёл бы. issued_date не трогаем — он остаётся датой
        # создания черновика, иначе check_dates начнёт ругаться на срок
        # раньше даты выдачи отложенных заданий.
        recomputed = False
        if sheet:
            due = sheet._next_lesson_datetime()
            if due and due != self.submission_date:
                self.sudo().write({'submission_date': due})
                recomputed = True

        # Текст и вложения сходятся до смены состояния. Учитель мог напечатать
        # ДЗ прямо в журнале и не сохранить; write по листу прогоняет через
        # тот же синк, что и сохранение журнала, и подтягивает текст в
        # задание (hw_skip_sync не ставим — тут это и есть цель).
        if sheet:
            sheet.sudo().write({'lesson_homework': sheet.lesson_homework})

        self.act_publish()

        # Объявление — один раз, здесь, с вложениями учителя.
        posted = False
        if sheet and hasattr(type(sheet), '_hw_channel_announce'):
            sheet._hw_channel_announce(
                self, 'created', attachments=self.material_ids)
            posted = bool(self.hw_channel_message_id)

        return {
            'success': True,
            'state': self.state,
            'posted': posted,
            'recomputed': recomputed,
            'submission_date': self.submission_date,
        }

    def action_hw_publish(self):
        """Кнопка «Выдать» в ПК-форме задания."""
        result = self.hw_publish()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Задание выдано'),
                'details': _('Срок сдачи: %s') % (
                    self.submission_date.strftime('%d.%m.%Y %H:%M')
                    if self.submission_date else '—'),
                'sticky': False,
                'next': {'type': 'reload'},
            },
        }