from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

import logging

_logger = logging.getLogger(__name__)


# Группы, которым доступна проверка работ. Завуч состоит в обеих
# (teacher + back_office), поэтому отдельной версии для него не нужно.
BULK_GROUPS = (
    'openeducat_assignment.group_op_assignment_user',
    'openeducat_assignment.group_teacher_assignment',
    'openeducat_core.group_op_faculty',
    'openeducat_core.group_op_back_office_admin',
)


class OpAssignment(models.Model):
    """Открытие окна проверки работ и массовые действия по выбору.

    ПОЧЕМУ ОКНО ОТДЕЛЬНОЕ, А НЕ СПИСОК В ФОРМЕ ЗАДАНИЯ.

    Штатные фильтры Odoo живут в search view, а search view монтируется
    только над отдельным action (list/pivot/graph). У one2many внутри
    формы задания своего action нет, поэтому `<filter>` к нему не
    подключается — и выбрать строки там тоже нельзя: механизм выбора
    работает только в отдельном list view.

    Проверено вживую на test4: домен в форме до сервера доходит (кнопка
    меняет подсветку, поле hw_filter пишется), но клиент домен к уже
    загруженным строкам вложенного списка не применяет — список остаётся
    прежним. Отсюда и третья попытка: фильтры и выбор строк сделаны так,
    как Odoo их поддерживает, — отдельное окно со своей search view.

    Окно одно на задание, вкладок нет — согласованная структура сохранена.
    """

    _inherit = 'op.assignment'

    def action_hw_open_works(self):
        """Окно работ — общее для кнопки «Ответы на задание».

        Штатная кнопка get_assignment_submissions в базовом модуле
        возвращает action без search view, поэтому фильтров и выбора
        строк в нём нет. Метод переопределён: кнопка открывает то же
        окно, что и раньше, но с фильтрами по состояниям и штатными
        галочками выбора.
        """
        self.ensure_one()
        if not any(self.env.user.has_group(g) for g in BULK_GROUPS):
            raise AccessError(
                _('Список работ доступен учителю и администрации'))
        if not self.assignment_sub_line:
            raise UserError(_('По этому заданию ещё нет работ'))

        action = self.env['ir.actions.act_window']._for_xml_id(
            'rost_lesson_homework.action_op_assignment_works')
        action['domain'] = [('assignment_id', '=', self.id)]
        action['context'] = {
            'default_assignment_id': self.id,
            'hw_assignment_id': self.id,
        }
        action['display_name'] = self.display_name
        return action

    def get_assignment_submissions(self):
        """Родная кнопка «Ответы на задание» — второй источник правды
        убрали, остаётся она одна (Миша: «надо оставить один»).

        Открывает наше окно работ: тот же список работ задания, но с
        фильтрами по состояниям и штатным выбором строк. Раньше метод
        возвращал action без search view, из-за чего фильтров там
        не было вовсе.
        """
        return self.action_hw_open_works()


class OpAssignmentSubLine(models.Model):
    """Работа: отметка и массовые действия по ВЫБРАННЫМ строкам.

    Отличие от прошлой панели в форме: отметка теперь настоящая,
    штатная — галочка выбора строки в list view. Кнопка над списком
    получает только те записи, которые клиент передал (self), поэтому
    подменять их поиском по полю не нужно и «зацепить» чужое невозможно.
    """

    _inherit = 'op.assignment.sub.line'

    hw_marked = fields.Boolean(
        string='Отмечено',
        help='Отметьте работы и примените действие из меню «Действия».')

    # Превью вложения для показа в списке работ.
    #
    # ЗАЧЕМ ЭТО ПОЛЕ. Ученик смотрит свои вложения в ФОРМЕ сдачи, где
    # attachment_ids отрисован виджетом many2many_binary — он рисует
    # превью с тапом. Учитель смотрит те же файлы в КОЛОНКЕ списка, а
    # many2many_binary в list view не рисует превью, а даёт ссылку с
    # download=true: картинку надо сначала скачать (Миша: «у него также
    # превью с тапом, но когда учитель получает ответ, то изображение
    # отображается ссылкой, которую необходимо сперва скачать»).
    #
    # attachment_image — штатный виджет Odoo для many2one: рисует
    # /web/image/<id>/300x300 и открывается по клику. Берём ПЕРВОЕ
    # вложение: если в ответе несколько файлов, в колонке показывается
    # первое, а полный список остаётся рядом (attachment_ids).
    hw_attachment_preview_id = fields.Many2one(
        'ir.attachment',
        string='Превью вложения',
        compute='_compute_hw_attachment_preview_id',
        help='Первое вложение работы — для превью в списке.')

    @api.depends('attachment_ids')
    def _compute_hw_attachment_preview_id(self):
        """Первое вложение работы — им заполняется превью в списке.

        Берём первое, а не «самое большое»: выбор должен быть
        предсказуемым, порядок attachment_ids задаёт сам ответ ученика.
        Файл берём из attachment_ids, а не поиском по ir.attachment:
        поле уже отфильтровано по res_model, значит чужие вложения с
        тем же res_id сюда не попадут.
        """
        for line in self:
            line.hw_attachment_preview_id = line.attachment_ids[:1].id or False

    def _hw_bulk_allowed(self):
        return any(self.env.user.has_group(g) for g in BULK_GROUPS)

    # ---------------------------------------------------------------
    # Массовые действия по выбору
    # ---------------------------------------------------------------
    def action_hw_accept_selected(self):
        return self._hw_apply_selected('accept')

    def action_hw_change_selected(self):
        return self._hw_apply_selected('change')

    def action_hw_reject_selected(self):
        return self._hw_apply_selected('reject')

    def _hw_apply_selected(self, state):
        """Применить состояние к работам, отмеченным штатными галочками.

        sudo() здесь НЕ используется намеренно: sudo снимает record
        rules, и учитель поправил бы чужое задание, а ученик принял бы
        чужие работы (проверено ранее: проходило без отказа).
        """
        if not self._hw_bulk_allowed():
            raise AccessError(
                _('Массовые действия доступны учителю и администрации'))
        if not self:
            raise UserError(_('Отметьте галочками хотя бы одну работу'))
        vals = {'state': state}
        note = self.env.context.get('hw_bulk_note')
        if note:
            vals['teacher_note'] = note
        marks = self.env.context.get('hw_bulk_marks')
        if marks:
            vals['marks'] = marks
        self.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

