from odoo import _, api, fields, models
from odoo.exceptions import AccessError

import logging

_logger = logging.getLogger(__name__)


# Группы, под которыми форма задания показывается в варианте учителя.
# Завуч состоит в обеих (teacher + manager), поэтому он видит ровно то же,
# что учитель, — отдельной версии для него не нужно.
TEACHER_GROUPS = (
    'openeducat_assignment.group_op_assignment_user',
    'openeducat_assignment.group_teacher_assignment',
    'openeducat_core.group_op_faculty',
)


def _hw_notify(record, message):
    """Штатное уведомление Odoo о результате действия."""
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': _('Готово'),
            'message': message,
            'type': 'success',
            'sticky': False,
        },
    }


class OpAssignment(models.Model):
    """Вид формы задания в ПК: разделение по ролям.

    Ключевое решение: НЕ делаем отдельные view с groups_id.

    В openeducat_assignment одна primary-архитектура (view_op_assignment_form)
    и никакого разделения по группам на уровне view не существует. Два
    варианта с разными groups_id дали бы пользователю, состоящему в обеих
    группах, ОБЕ версии сразу. А such есть: 17 преподавателей test4 состоят
    и в group_student_assignment (включая завучу), то есть почти каждый
    учитель попадает в этот случай.

    Поэтому разделение сделано на элементах одной формы:
      * groups= на полях и вкладках — прячет то, что ученику не нужно;
      * домен списка работ — серверный, по роли (hw_sub_line_domain).

    Никакого своего JavaScript: фильтры — штатные кнопки Odoo, каждая
    открывает эту же форму с другим контекстом.
    """

    _inherit = 'op.assignment'

    # Домен для списка работ, подставляемый в поле во вкладке «Работы».
    # Одно поле вместо кучи условий invisible в разметке: сервер решает,
    # что показать, и ученик физически не получает чужие строки.
    hw_sub_line_domain = fields.Char(
        string='Фильтр работ',
        compute='_compute_hw_sub_line_domain',
        help='Домен списка работ. Учитель видит весь класс, ученик — '
             'только свою работу.')

    hw_filter = fields.Selection(
        selection=[
            ('all', 'Все'),
            ('nosub', 'Не сдали'),
            ('wait', 'Ждут проверки'),
            ('ok', 'Принято'),
            ('back', 'На доработке'),
        ],
        string='Фильтр',
        default='all',
        help='Выбранный фильтр списка работ. Меняется штатными кнопками '
             'в форме.')

    # Состояния для каждого значения фильтра. Один источник правды для
    # домена (_compute_hw_sub_line_domain) и для массовых действий.
    HW_FILTER_STATES = {
        'nosub': ['draft'],
        'wait': ['submit'],
        'ok': ['accept'],
        'back': ['change'],
    }

    # ---------------------------------------------------------------
    # Домен по роли
    # ---------------------------------------------------------------
    def _hw_is_teacher(self):
        """Считаем ли мы текущего пользователя тем, кто проверяет работы."""
        self.ensure_one()
        return bool(self.env.user.has_group(
            'openeducat_assignment.group_op_assignment_user')
            or self.env.user.has_group(
                'openeducat_assignment.group_teacher_assignment')
            or self.env.user.has_group('openeducat_core.group_op_faculty'))

    @api.depends('batch_id')
    @api.depends_context('hw_filter', 'uid')
    def _compute_hw_sub_line_domain(self):
        """Домен для one2many работ.

        Ключ фильтра берём из контекста: кнопки в форме подставляют
        hw_filter, а мы превращаем его в домен по полю state.

        Состояния в op.assignment.sub.line.state:
          draft  — не сдавал
          submit — сдал, ждёт проверки
          accept — принято
          change — на доработке
          reject — отклонено
        """
        KEYS = dict(self.HW_FILTER_STATES, all=None)
        for asg in self:
            if not asg._hw_is_teacher():
                # Ученик видит только свою строку — по student_id, а не по
                # классу: иначе откроется весь параллельный список.
                asg.hw_sub_line_domain = [
                    ('student_id.user_id', '=', self.env.user.id)
                ]
                continue
            states = KEYS.get(self.env.context.get('hw_filter') or 'all')
            dom = []
            if states:
                dom = [('state', 'in', states)]
            # Незавершённые работы показываем, принятые — подсвечивает
            # сама list через decoration-success.
            asg.hw_sub_line_domain = dom or [('id', '!=', 0)]

    # ---------------------------------------------------------------
    # Штатные кнопки фильтра
    # ---------------------------------------------------------------
    def _hw_filter_action(self, key):
        """Открыть эту же форму с другим фильтром.

        Кнопки в форме объявлены type="action" не могут, поэтому они
        type="object" и возвращают act_window. Это штатный механизм Odoo:
        сервер отдаёт действие, клиент его исполняет. Своего JS нет.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Домашнее задание'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': dict(self.env.context, hw_filter=key),
        }

    def action_hw_filter_all(self):
        return self._hw_filter_action('all')

    def action_hw_filter_nosub(self):
        return self._hw_filter_action('nosub')

    def action_hw_filter_wait(self):
        return self._hw_filter_action('wait')

    def action_hw_filter_ok(self):
        return self._hw_filter_action('ok')

    def action_hw_filter_back(self):
        return self._hw_filter_action('back')

    # ---------------------------------------------------------
    # Массовые действия — штатный эквивалент панели из макета.
    #
    # В макете design/homework-pc-teacher-form-v2.html панель выглядит
    # как «Выбрано N ▸ Принять / На доработку / Отклонить ▸ Оценка ▸
    # Комментарий ▸ Применить» — с галочками и своим JS.
    #
    # Галочек выбрать строки в Odoo в списке ВНУТРИ формы нет: выбор
    # работает только в отдельном list view (action), где есть панель
    # «N выбрано». Поэтому здесь кнопка применяется ко ВСЕМ строкам
    # под текущим фильтром, а не к отмеченным. Сузить выбор можно
    # фильтром — это то же самое по смыслу.
    #
    # Оценка и комментарий берутся из полей ниже; пустые не применяются.
    # ---------------------------------------------------------
    hw_bulk_marks = fields.Float(string='Оценка пачкой')
    hw_bulk_note = fields.Char(string='Комментарий пачкой')

    def _hw_bulk_targets(self):
        """Строки работ под текущим фильтром — их и меняем."""
        self.ensure_one()
        domain = [('assignment_id', '=', self.id)]
        filt = list(self._hw_filter_states())
        if filt:
            domain += [('state', 'in', filt)]
        return self.env['op.assignment.sub.line'].search(domain)

    def _hw_filter_states(self):
        """Состояния текущего фильтра; пустой список — все."""
        return self.HW_FILTER_STATES.get(
            self.env.context.get('hw_filter') or 'all') or []

    def _hw_bulk_write(self, state):
        """Массовое действие ПОД ТЕКУЩИМ ФИЛЬТРОМ.

        sudo() здесь НЕ используется намеренно. Раньше стоял — и это была
        дыра: sudo снимает record rules, поэтому ученик вызовом этого
        метода мог принять чужие работы, а учитель — поправить чужое
        задание. Проверено: оба вызова проходили без отказа.

        Без sudo домен ищется под текущим пользователем, поэтому
        применяются ровно те строки, что видны в списке.

        Проверка роли — обязательна и на сервере: группы на панели в
        разметке скрывают кнопки от клиента, но RPC можно вызвать
        напрямую, минуя форму.
        """
        self.ensure_one()
        if not self._hw_is_teacher() and not self.env.user.has_group(
                'openeducat_core.group_op_back_office_admin'):
            raise AccessError(
                _('Массовые действия по работам доступны учителю и админу'))
        lines = self._hw_bulk_targets()
        if not lines:
            return _hw_notify(self, _('Нет строк под текущим фильтром'))
        vals = {'state': state}
        if self.hw_bulk_marks:
            vals['marks'] = self.hw_bulk_marks
        if self.hw_bulk_note:
            vals['teacher_note'] = self.hw_bulk_note
        lines.write(vals)
        return _hw_notify(
            self, _('Изменено строк: %d') % len(lines))

    def action_hw_bulk_accept(self):
        return self._hw_bulk_write('accept')

    def action_hw_bulk_change(self):
        return self._hw_bulk_write('change')

    def action_hw_bulk_reject(self):
        return self._hw_bulk_write('reject')

    # ---------------------------------------------------------
    # Активный фильтр: та же кнопка, но серверной подсветкой.
    # Нужна вторая кнопка потому, что Odoo не умеет менять class
    # поляны по значению: показывать все кнопки и выделять активную
    # можно только двумя наборами с взаимоисключающим invisible.
    # ---------------------------------------------------------
    def action_hw_filter_all_active(self):
        return self._hw_filter_action('all')

    def action_hw_filter_nosub_active(self):
        return self._hw_filter_action('nosub')

    def action_hw_filter_wait_active(self):
        return self._hw_filter_action('wait')

    def action_hw_filter_ok_active(self):
        return self._hw_filter_action('ok')

    def action_hw_filter_back_active(self):
        return self._hw_filter_action('back')

    # ---------------------------------------------------------------
    # Ученик: заменить список работ на свою единственную работу
    # ---------------------------------------------------------------
    def action_hw_my_work(self):
        """Кнопка «Моя работа» — открыть карточку своей сдачи.

        Ученику не нужен список из чужого класса: он открывает свою
        строку напрямую. Учителю кнопка не показывается.
        """
        self.ensure_one()
        work = self.env['op.assignment.sub.line'].search([
            ('assignment_id', '=', self.id),
            ('student_id.user_id', '=', self.env.user.id),
        ], limit=1)
        if not work:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Работа не сдана'),
                    'message': _('Ты ещё не сдавал это задание.'),
                    'type': 'info',
                    'sticky': False,
                },
            }
        return work.action_open_form_view() if hasattr(
            work, 'action_open_form_view') else {
            'type': 'ir.actions.act_window',
            'name': _('Моя работа'),
            'res_model': work._name,
            'res_id': work.id,
            'view_mode': 'form',
            'target': 'current',
        }