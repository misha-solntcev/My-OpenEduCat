/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("attendance_teacher_tour", {
    url: "/web",
    steps: () => [
        {
            id: "attendance_main_menu",
            trigger: '.o_app[data-menu-xmlid="openeducat_attendance.menu_op_attendance_root"]',
            content: _t("Начните работу здесь."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            id: "attendance_sheet_menu",
            trigger: 'a[data-menu-xmlid="openeducat_attendance.menu_op_attendance_sheet_sub"]',
            content: _t("Откройте журналы."),
            tooltipPosition: "right",
            run: "click",
        },
        {
            id: "select_first_row",
            trigger: ".o_list_renderer .o_data_row:first-child",
            content: _t("Выберите урок."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            id: "start_lesson",
            trigger: ".o_attendance_start_btn",
            content: _t("Нажмите 'Начать урок'."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            id: "mark_present",
            trigger: ".o_attendance_present_all_btn",
            content: _t("Отметьте всех присутствующими."),
            tooltipPosition: "top",
            run: "click",
        },
        {
            id: "finish_lesson",
            trigger: ".o_attendance_done_btn",
            content: _t("Завершите урок."),
            tooltipPosition: "bottom",
            run: "click",
        }
    ]
});