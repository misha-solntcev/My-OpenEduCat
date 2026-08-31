/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";

// Ограничение сетки недели/дня рабочими часами школы (СПб):
// уроки начинаются не раньше 09:00, реальный максимум конца — 17:40 (см. op_session за 2025-09..2026-04).
const SLOT_MIN_TIME = "09:00:00";
const SLOT_MAX_TIME = "18:00:00";

export class SessionCalendarCommonRenderer extends CalendarCommonRenderer {
    /**
     * @override
     * Добавляем FullCalendar slotMinTime/slotMaxTime, чтобы сетка
     * показывала только 09:00–18:00 вместо полных суток.
     */
    get options() {
        return {
            ...super.options,
            slotMinTime: SLOT_MIN_TIME,
            slotMaxTime: SLOT_MAX_TIME,
            // Школа работает по СПб: показываем сетку и уроки в Europe/Moscow
            // независимо от локального пояса пользователя.
            timeZone: "Europe/Moscow",
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
