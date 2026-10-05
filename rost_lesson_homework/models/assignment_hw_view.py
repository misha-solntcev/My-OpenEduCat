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


    def _hw_is_teacher(self):
        """Считаем ли мы текущего пользователя тем, кто проверяет работы."""
        self.ensure_one()
        return bool(self.env.user.has_group(
            'openeducat_assignment.group_op_assignment_user')
            or self.env.user.has_group(
                'openeducat_assignment.group_teacher_assignment')
            or self.env.user.has_group('openeducat_core.group_op_faculty'))

    @api.depends('batch_id')
    def _compute_hw_sub_line_domain(self):
        """Домен для вложенного one2many работ — по роли, не по фильтру.

        Фильтра по состояниям здесь нет и быть не может: фильтры в Odoo
        живут только в search view над отдельным action, а у вложенного
        one2many своего action нет. Домен из этого поля клиент к уже
        загруженным строкам не применяет — проверено вживую на test4.
        Поэтому фильтры вынесены в отдельное окно работ
        (assignment_sub_line_works_view.xml), а здесь остаётся только
        разграничение по роли.

        Состояния в op.assignment.sub.line.state:
          draft  — не сдавал
          submit — сдал, ждёт проверки
          accept — принято
          change — на доработке
          reject — отклонено
        """
        for asg in self:
            if not asg._hw_is_teacher():
                # Ученик видит только свою строку — по student_id, а не по
                # классу: иначе откроется весь параллельный список.
                asg.hw_sub_line_domain = [
                    ('student_id.user_id', '=', self.env.user.id)
                ]
            else:
                # Учителю, завучу и админу — все работы задания.
                asg.hw_sub_line_domain = [('id', '!=', 0)]
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