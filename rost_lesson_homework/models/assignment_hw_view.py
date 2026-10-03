from odoo import _, api, fields, models

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
        KEYS = {
            'all': None,
            'nosub': ['draft'],
            'wait': ['submit'],
            'ok': ['accept'],
            'back': ['change'],
        }
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