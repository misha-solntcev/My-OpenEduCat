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
            'title': 'Готово',
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
        groups='openeducat_assignment.group_op_assignment_user,'
               'openeducat_assignment.group_teacher_assignment,'
               'openeducat_core.group_op_faculty,'
               'openeducat_core.group_op_back_office_admin',
        help='Выбранный фильтр списка работ. Меняется штатными кнопками '
             'в форме.')

    # Фильтр — ИМЕННО запись, а не только контекст.
    #
    # Сначала фильтр жил в context: кнопка возвращала act_window с
    # context hw_filter, а домен считался через depends_context. Так он
    # не работал: клиент не перечитывает запись при смене контекста,
    # значение hw_sub_line_domain оставалось прежним, и список не
    # менялся (Миша: «фильтры не работают»).
    #
    # Теперь кнопка пишет поле и просит клиента перечитать форму
    # (tag: reload) — тогда сервер отдаёт и фильтр, и новый домен.
    HW_FILTER_BTN_GROUPS = (
        'openeducat_assignment.group_op_assignment_user',
        'openeducat_assignment.group_teacher_assignment',
        'openeducat_core.group_op_faculty',
        'openeducat_core.group_op_back_office_admin',
    )

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

    @api.depends('hw_filter', 'batch_id')
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
            states = KEYS.get(asg.hw_filter or 'all')
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
        """Выбрать фильтр и обновить список.

        Кнопки в форме объявлены type="action" не могут, поэтому они
        type="object" и возвращают act_window. Это штатный механизм Odoo:
        сервер отдаёт действие, клиент его исполняет. Своего JS нет.

        ВАЖНО: фильтр пишется в запись (hw_filter), а не только в
        context. Через context не работало: клиент при смене контекста
        не перечитывает запись, значение hw_sub_line_domain оставалось
        прежним, и список не менялся. Поэтому пишем поле и просим
        клиента перечитать форму — тогда сервер отдаёт новый домен.
        """
        self.ensure_one()
        if not any(self.env.user.has_group(g)
                   for g in self.HW_FILTER_BTN_GROUPS):
            raise AccessError(
                _('Фильтр по работам доступен учителю и админу'))
        if self.hw_filter != key:
            # sudo здесь не нужен и не нужен НИКОГДА: поле hw_filter
            # открыто учителю в его задании. Но писать его может только
            # тот, кому запись разрешена правилами — заодно проверяем.
            self.write({'hw_filter': key})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
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
    # Полоса-сводка из макета: «Работы — 15 · 11 сдали · 8 принято ·
    # 2 ждут проверки · 1 на доработке». Считается на сервере, без JS.
    # ---------------------------------------------------------
    hw_count_total = fields.Integer(
        string='Работ всего', compute='_compute_hw_counts')
    hw_count_submitted = fields.Integer(
        string='Сдали', compute='_compute_hw_counts')
    hw_count_accept = fields.Integer(
        string='Принято', compute='_compute_hw_counts')
    hw_count_wait = fields.Integer(
        string='Ждут проверки', compute='_compute_hw_counts')
    hw_count_change = fields.Integer(
        string='На доработке', compute='_compute_hw_counts')
    hw_count_draft = fields.Integer(
        string='Не сдали', compute='_compute_hw_counts')

    def _compute_hw_counts(self):
        """Пересчёт сводки. Считаем по всем работам задания, а не по
        фильтру: полоса показывает картину целиком, иначе при переключении
        фильтра цифры прыгали бы и путались."""
        for asg in self:
            grouped = self.env['op.assignment.sub.line']._read_group(
                [('assignment_id', '=', asg.id)],
                groupby=['state'],
                aggregates=['__count'])
            by_state = {g[0]: g[1] for g in grouped}
            asg.hw_count_total = sum(by_state.values())
            asg.hw_count_accept = by_state.get('accept', 0)
            asg.hw_count_wait = by_state.get('submit', 0)
            asg.hw_count_change = by_state.get('change', 0)
            asg.hw_count_draft = by_state.get('draft', 0)
            # «Сдали» — все, кто не в draft: сдал, даже если на доработке.
            asg.hw_count_submitted = (
                asg.hw_count_total - by_state.get('draft', 0))


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