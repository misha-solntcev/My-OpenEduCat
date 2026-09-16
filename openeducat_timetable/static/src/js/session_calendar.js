/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";

// В Odoo 18 @web/core/l10n/dates не экспортирует класс DateTime —
// ядро берёт luxon из глобала (см. calendar_common_renderer.js).
const { DateTime } = luxon;

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
