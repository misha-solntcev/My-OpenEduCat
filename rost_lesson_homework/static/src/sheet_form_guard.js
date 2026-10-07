/**
 * Охрана выхода из журнала урока (2026-10).
 *
 * beforeLeave у штатного FormController сохраняет грязную форму и молча
 * пропускает выход. Для журнала этого мало: ДЗ может быть СОХРАНЕНО
 * черновиком — учитель ушёл со страницы, задание так и не выдано,
 * ученики его не видят (кейс Макаровой, 2026-10-07). До этого
 * единственная точка выдачи была в форме задания, куда из журнала
 * не ведёт ничего.
 *
 * Здесь: пока ДЗ урока в состоянии draft, уход со страницы показывает
 * подтверждение. Отмена возвращает в журнал; согласие — штатный beforeLeave
 * (автосохранение, если форма грязная). Механика clearUncommittedChanges:
 * коллбэк, вернувший false, блокирует навигацию — так же работает
 * _confirmSave в settings_form_controller.
 *
 * js_class="sheet_form_guard" ставится на форму журнала в
 * views/attendance_sheet_homework_view.xml. Поле homework_state должно
 * быть в arch (там оно invisible="1") — контроллер читает его из data.
 */
/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/views/registry";
import { FormController } from "@web/views/form/form_controller";
import { FormView } from "@web/views/form/form_view";

export class SheetFormController extends FormController {
    async beforeLeave() {
        const root = this.model.root;
        if (
            root &&
            !root.isNew &&
            root.resModel === "op.attendance.sheet" &&
            root.data &&
            root.data.homework_state === "draft"
        ) {
            const proceed = await new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    title: "Домашнее задание не выдано",
                    body: "ДЗ сохранено черновиком — ученики его пока не видят. Выйти со страницы журнала?",
                    confirmLabel: "Выйти",
                    cancelLabel: "Остаться",
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });
            if (!proceed) {
                return false;
            }
        }
        return super.beforeLeave();
    }
}

registry
    .category("views")
    .add("sheet_form_guard", { ...FormView, Controller: SheetFormController });