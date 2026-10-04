from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

import logging

_logger = logging.getLogger(__name__)


# Группы, которым доступна проверка работ пачкой. Завуч состоит в обеих
# (teacher + back_office), поэтому отдельной версии для него не нужно.
BULK_GROUPS = (
    'openeducat_assignment.group_op_assignment_user',
    'openeducat_assignment.group_teacher_assignment',
    'openeducat_core.group_op_faculty',
    'openeducat_core.group_op_back_office_admin',
)


class OpAssignmentSubLine(models.Model):
    """Отметка строки для массовых действий.

    В макете design/homework-pc-teacher-form-v2.html отметка — галочка в
    первой колонке, нарисованная своим JS. Штатно выбрать строки в
    списке ВНУТРИ формы нельзя: механизм выбора в Odoo работает только в
    отдельном list view (action). Поэтому отметка сделана обычным полем
    строки — это штатный Odoo, свой JS не нужен.
    """

    _inherit = 'op.assignment.sub.line'

    hw_marked = fields.Boolean(
        string='Отмечено',
        help='Отметьте строки, затем примените действие пачкой в панели '
             'над списком.')

    def _hw_bulk_allowed(self):
        return any(self.env.user.has_group(g) for g in BULK_GROUPS)


class OpAssignment(models.Model):
    """Массовые действия по работам — как панель в макете.

    Панель в макете: «Выбрано N ▸ Принять / На доработку / Отклонить ▸
    Оценка ▸ Комментарий ▸ Применить». Кнопки состояния НАПРАВЛЯЮТ (запоминают
    что применить), а «Применить» выполняет. Панель видна только когда
    отмечены строки.

    Отметки живут в строках (hw_marked), поэтому панель не выходит за
    пределы одного задания и после reload остаётся согласованной с
    самим списком.
    """

    _inherit = 'op.assignment'

    hw_bulk_state = fields.Selection(
        selection=[
            ('accept', 'Принять'),
            ('change', 'На доработку'),
            ('reject', 'Отклонить'),
        ],
        string='Что применить',
        help='Выбранное действие применяется к отмеченным работам кнопкой '
             '«Применить».')

    hw_bulk_marks = fields.Float(string='Оценка пачкой')
    hw_bulk_note = fields.Char(string='Комментарий пачкой')

    hw_bulk_count = fields.Integer(
        string='Отмечено', compute='_compute_hw_bulk_count')

    def _hw_bulk_allowed(self):
        """Может ли текущий пользователь проверять работы пачкой."""
        return any(self.env.user.has_group(g) for g in BULK_GROUPS)

    def _hw_marked_lines(self):
        """Отмеченные работы ЭТОГО задания — то, к чему применяем действие."""
        self.ensure_one()
        return self.env['op.assignment.sub.line'].search([
            ('assignment_id', '=', self.id),
            ('hw_marked', '=', True),
        ])

    @api.depends('assignment_sub_line.hw_marked')
    def _compute_hw_bulk_count(self):
        for asg in self:
            asg.hw_bulk_count = len(asg._hw_marked_lines())

    # ---------------------------------------------------------------
    # Кнопки панели: первые три выбирают действие
    # ---------------------------------------------------------------
    def _hw_bulk_pick(self, state):
        self.ensure_one()
        if not self._hw_marked_lines():
            raise UserError(_('Отметьте хотя бы одну работу'))
        self.hw_bulk_state = state
        label = dict(
            self._fields['hw_bulk_state'].selection).get(state, '')
        return _hw_notify(
            _('Выбрано действие «%s». Нажмите «Применить».') % label)

    def action_hw_bulk_mark_accept(self):
        return self._hw_bulk_pick('accept')

    def action_hw_bulk_mark_change(self):
        return self._hw_bulk_pick('change')

    def action_hw_bulk_mark_reject(self):
        return self._hw_bulk_pick('reject')

    # ---------------------------------------------------------------
    # Применение
    # ---------------------------------------------------------------
    def action_hw_bulk_apply(self):
        """Применить выбранное действие к отмеченным работам.

        sudo() здесь НЕ используется намеренно: sudo снимает record rules,
        и ученик вызовом этого метода принял бы чужие работы, а учитель
        поправил бы чужое задание (проверено: проходило без отказа).

        Проверка роли обязательна и на сервере: groups= в разметке прячет
        кнопки от клиента, но RPC вызывается напрямую, мимо формы.

        Отметки снимаем после применения — как в макете: выбрано N, применили,
        панель пропала до следующего выбора.
        """
        self.ensure_one()
        if not (self._hw_bulk_allowed()
                or self.env.user.has_group(
                    'openeducat_core.group_op_back_office_admin')):
            raise AccessError(
                _('Массовые действия доступны учителю и администрации'))

        lines = self._hw_marked_lines()
        if not lines:
            raise UserError(_('Отметьте хотя бы одну работу'))
        if not self.hw_bulk_state:
            raise UserError(
                _('Выберите действие: Принять, На доработку или Отклонить'))

        vals = {'state': self.hw_bulk_state, 'hw_marked': False}
        # Пустые поля не применяются, чтобы не затирать прежние значения.
        if self.hw_bulk_marks:
            vals['marks'] = self.hw_bulk_marks
        if self.hw_bulk_note:
            vals['teacher_note'] = self.hw_bulk_note
        lines.write(vals)
        self.hw_bulk_marks = 0
        self.hw_bulk_note = False
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


def _hw_notify(message):
    """Штатное уведомление Odoo о результате действия.

    Без _(): эта функция вызывается из тела класса, и переводчик не
    находит в стеке кадр модели — падало «no translation language
    detected». Сообщение уже переведено вызывающим кодом.
    """
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Готово',
            'message': message,
            'type': 'success',
            'sticky': False,
        },
    }