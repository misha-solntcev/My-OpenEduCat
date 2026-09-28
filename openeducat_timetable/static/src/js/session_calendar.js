/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { useState, onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

// В Odoo 18 @web/core/l10n/dates не экспортирует класс DateTime —
// ядро берёт luxon из глобала (см. calendar_common_renderer.js).
const { DateTime } = luxon;

// Попап урока: кнопка Edit — завучу и УЧИТЕЛЮ, но учителю только на его
// собственных уроках. Delete — только завучу (ACL на unlink у учителя 0).
// CalendarCommonPopover.isEventEditable в Odoo 18 жёстко `return true`,
// поэтому штатно кнопка горит у всех, кто попал в «Расписание».
// Ученику она ничего не даёт (прав на запись нет) — убираем.
//
// Учителю Edit нужен как вход в форму урока, а оттуда — кнопка
// «Attendance Sheet» (openeducat_attendance) ведёт в журнал урока.
// Право на write у учителя ограничено rule'ом teacher_session_write_rule
// (faculty_id.user_id == user), поэтому на чужом уроке Edit не показываем:
// открылась бы форма, в которой всё равно нельзя ничего сохранить, а журнал
// чужого урока учителю видеть не нужно.
//
// ВАЖНО: user.hasGroup() возвращает Promise (LazyCache.read), а не boolean.
// Без await геттер отдаёт Promise — объект, который всегда truthy, и кнопка
// осталась бы у всех. Ядро делает так же: см. list_controller.js:109
// (`await user.hasGroup(...)`) и export_all.js:37.
class SessionPopover extends CalendarCommonPopover {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({
            isTimetableManager: false,
            isTeacher: false,
            ownFacultyIds: [],
        });
        onWillStart(async () => {
            const [isManager, isTeacher] = await Promise.all([
                user.hasGroup("openeducat_timetable.group_op_timetable_manager"),
                user.hasGroup("openeducat_timetable.group_teacher_timetable"),
            ]);
            this.state.isTimetableManager = isManager;
            this.state.isTeacher = isTeacher;
            if (isTeacher) {
                // свои faculty_id нужны, чтобы отличить свой урок от чужого
                this.state.ownFacultyIds = await this.orm.search(
                    "op.faculty",
                    [["user_id", "=", user.userId]],
                    { limit: 100 }
                );
            }
        });
    }
    get isOwnLesson() {
        const faculty = this.props.record?.data?.faculty_id;
        // many2one приходит кортежем [id, display_name]
        const facultyId = Array.isArray(faculty) ? faculty[0] : faculty;
        return !!facultyId && this.state.ownFacultyIds.includes(facultyId);
    }
    get isEventEditable() {
        if (this.state.isTimetableManager) {
            return true;
        }
        return this.state.isTeacher && this.isOwnLesson;
    }
    get isEventDeletable() {
        return this.state.isTimetableManager && this.props.model.canDelete;
    }
}

// Зона нативная (браузер), как в стоковом календаре: дни/недели правильные
// у всех, время уроков локальное. Раньше здесь были timeZone: "Europe/Moscow"
// и initialDate из DateTime.now().setZone("Europe/Moscow") — связка ломала
// навигацию: week/day листаются через перемонтирование (calendarKey = scale +
// date.valueOf()), initialDate снова брал «сейчас», и сетка всегда
// возвращалась на текущую неделю (прошлое/будущее недоступны).

// Окно сетки недели/дня = учебный день школы 09:00–19:00 по Москве.
// Рендер нативный, в зоне браузера, поэтому границы пересчитываем в локальную
// зону: у СПб-юзера (сдвиг 0) окно 09:00–19:00, у удалённого (Иркутск +08)
// тот же интервал = 14:00–24:00 местного.
function schoolWindowLocal() {
    const now = DateTime.now();
    const deltaMin = now.offset - now.setZone("Europe/Moscow").offset;
    const fmt = (totalMin) => {
        // 1440 = полночь следующего дня → FullCalendar ждёт "24:00:00"
        if (totalMin === 1440) {
            return "24:00:00";
        }
        const t = ((totalMin % 1440) + 1440) % 1440;
        const h = String(Math.floor(t / 60)).padStart(2, "0");
        const m = String(t % 60).padStart(2, "0");
        return `${h}:${m}:00`;
    };
    return {
        min: fmt(9 * 60 + deltaMin),
        max: fmt(19 * 60 + deltaMin),
    };
}

export class SessionCalendarCommonRenderer extends CalendarCommonRenderer {
    /**
     * Попап урока вместо стокового: без Edit/Delete у всех, кроме завуч.
     */
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: SessionPopover,
    };

    /**
     * @override
     * Добавляем FullCalendar slotMinTime/slotMaxTime — сетка от начала
     * занятий (09:00 MSK) до конца учебного дня (19:00 MSK), в локальном
     * эквиваленте.
     */
    get options() {
        const { min, max } = schoolWindowLocal();
        return {
            ...super.options,
            slotMinTime: min,
            slotMaxTime: max,
        };
    }
}

import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { calendarView } from "@web/views/calendar/calendar_view";
import { registry } from "@web/core/registry";

export class SessionCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: SessionCalendarCommonRenderer,
        week: SessionCalendarCommonRenderer,
        month: CalendarRenderer.components.month,
        year: CalendarRenderer.components.year,
    };
}

registry.category("views").add("session_calendar", {
    ...calendarView,
    Renderer: SessionCalendarRenderer,
});
