from odoo import _, models
from odoo.exceptions import AccessError

import logging

_logger = logging.getLogger(__name__)


# Поля расписания, которые меняет ТОЛЬКО администрация.
# Учителю нужна ровно одна вещь: перевести состояние своего урока
# (журнал урока открывается по этим состояниям).
SCHEDULE_FIELDS = {
    'timetable_date', 'start_datetime', 'end_datetime',
    'timing_id', 'timing', 'days_id',
    'subject_id', 'batch_id', 'faculty_id', 'classroom_id',
    'timetable_id', 'academic_year_id', 'sequence', 'name',
    'conflict_override', 'active',
}

# Поля, доступные учителю на своей сессии.
TEACHER_FIELDS = {'state'}


class OpSession(models.Model):
    """Учитель ведёт журнал урока, но не меняет расписание.

    Требование Миши (2026-10-04): расписание изменяют только админы.
    Учитель при этом ставит оценки в журнале, а журнал открывается по
    состоянию урока (lecture_start -> state='start'), поэтому запись в
    op.session нужна — но только поле state, на своих уроках.

    Реализация: в write() отсекаем поля расписания для не-админов.
    ACL трогать нельзя — иначе учитель потеряет и state, и кнопки
    журнала, а вернуть их отдельным ACL для одного поля нельзя
    (ACL работает на уровне модели, не на уровне полей).
    """

    _inherit = 'op.session'

    def _hw_is_schedule_admin(self):
        """Кто имеет право менять само расписание."""
        return self.env.user.has_group(
            'openeducat_timetable.group_op_timetable_manager') or \
            self.env.su or self.env.is_superuser()

    def write(self, vals):
        # sudo-обходы (миграции, кроны, мастер расписания) не трогаем.
        if not vals or self._hw_is_schedule_admin():
            return super().write(vals)

        touched = SCHEDULE_FIELDS.intersection(vals)
        if not touched:
            return super().write(vals)

        # Преподавателю нельзя перебросить чужой урок и нельзя трогать сетку.
        # Убираем запрещённые поля из запроса, а если это вся запись —
        # отказываем явно, чтобы интерфейс не делал вид, что преуспела.
        allowed = {k: v for k, v in vals.items() if k not in touched}
        if not allowed:
            raise AccessError(
                _('Расписание изменяет только администрация. '
                  'Учитель ведёт журнал урока и состояние своего урока.')
            )
        return super().write(allowed)