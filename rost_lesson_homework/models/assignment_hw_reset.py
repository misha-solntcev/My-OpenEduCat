# -*- coding: utf-8 -*-
"""Полная очистка домашнего задания — СЛУЖЕБНАЯ, для тестирования.

Что делает (2026-10-02, согласовано с Мишей):
    снимает выдачу и удаляет все сдачи вместе с оценками, возвращает задание
    в черновик, сносит объявление из канала. Нужна, чтобы тестировать выдачу
    на одном и том же задании многократно — без неё старая принятая сдача
    переживает перевыдачу, и задание сразу попадает в «Проверено».

Видимость — только у Миши, через ir.config_parameter:
    rost_lesson_homework.allow_hw_reset = 1

Почему параметр, а не группа: кнопка нужна для тестов, а не учителю. Решение
о показе учителю не принято, и пока группа «учитель ДЗ» трогать рано — это
менять права на проде. Параметр переключается без -u и без правок ACL.

Кнопки в ПК-версии НЕТ (решение Миши 2026-10-02) — только миниапп. Поэтому
метод живёт здесь, а не в XML: серверное действие одно, вызывает его
миниапп, а окошко подтверждения рисует клиент.

Удаление — штатными методами Odoo. Никаких sudo().unlink(): unlink на
op.assignment.sub.line и так разрешён любому, у кого есть группа
group_op_assignment_user (учитель имеет её), а guard внутри unlink пропускает
членов этой группы. Обходить его не нужно — иначе сдачи удалялись бы в обход
правил, и метод перестал бы вести себя как код Odoo.

ВНИМАНИЕ: операция необратима для уже сданного. Подтверждения метод не
показывает — это делает вызывающий, поэтому ПК и миниапп смогут нарисовать
своё окно. Отсюда preview(), который ничего не меняет.
"""

import logging

from odoo import _, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

RESET_PARAM = 'rost_lesson_homework.allow_hw_reset'


class OpAssignmentHwReset(models.Model):
    _inherit = 'op.assignment'

    # ------------------------------------------------------------------
    # видимость
    # ------------------------------------------------------------------
    @property
    def _hw_reset_allowed(self):
        """Кнопка очистки доступна только когда параметр выставлен."""
        param = self.env['ir.config_parameter'].sudo().get_param(RESET_PARAM)
        return str(param).strip().lower() in ('1', 'true', 'yes', 'on')

    # ------------------------------------------------------------------
    # что будет удалено — для диалога подтверждения
    # ------------------------------------------------------------------
    def hw_reset_preview(self):
        """Счётчики для подтверждения. Ничего не меняет."""
        self.ensure_one()
        subs = self.assignment_sub_line
        graded = subs.filtered(lambda s: bool(s.marks))
        return {
            'assignment_id': self.id,
            'name': self.name or '',
            'state': self.state,
            'submissions': len(subs),
            'graded': len(graded),
            'attachments': len(subs.mapped('attachment_ids')),
            'in_channel': bool(self.hw_channel_message_id),
            'students': len(self.allocation_ids),
        }

    # ------------------------------------------------------------------
    # сама очистка
    # ------------------------------------------------------------------
    def hw_reset_clear(self):
        """Снять выдачу, удалить сдачи с оценками, вернуть в черновик.

        Возвращает что фактически удалено — вызывающий показывает это в
        результате операции.
        """
        if not self._hw_reset_allowed:
            raise AccessError(
                _('Очистка задания отключена. Нужно выставить параметр %s.')
                % RESET_PARAM)
        self.ensure_one()

        before = self.hw_reset_preview()
        subs = self.assignment_sub_line

        # Вложения сдачи удаляем до сдач: они висят на ir.attachment с
        # res_field, и после unlink сдачи осиротеют. unlink у вложений
        # штатный, ограничений на удаление нет.
        if subs.mapped('attachment_ids'):
            subs.mapped('attachment_ids').unlink()

        # Сдачи — обычным unlink. Guard в op.assignment.sub.line.unlink
        # пропускает членов group_op_assignment_user, то есть учителя.
        if subs:
            subs.unlink()

        # Объявление из канала — так же, как при отзыве задания.
        self.hw_drop_channel_post()

        # Возврат в черновик. Пишем state напрямую, а не act_set_to_draft:
        # тот меняет только state и не трогает пост, а нам нужен полный сброс.
        self.write({'state': 'draft'})

        result = {
            'removed_submissions': before['submissions'],
            'removed_graded': before['graded'],
            'removed_attachments': before['attachments'],
            'removed_post': before['in_channel'],
            'state': self.state,
        }
        _logger.info(
            'HW reset: assignment %s (%s) — снято сдач: %s, с оценками: %s',
            self.id, self.name, result['removed_submissions'],
            result['removed_graded'])
        return result

    # ------------------------------------------------------------------
    # включение/выключение (для Миши, без -u)
    # ------------------------------------------------------------------
    def hw_reset_enable(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param(RESET_PARAM, '1')
        return True

    def hw_reset_disable(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param(RESET_PARAM, '0')
        return True