/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";

export class SubjectGradesFormController extends FormController {
    setup() {
        super.setup();
        
        // При изменении значения поля current_quarter переключаем вкладку
        this.env.bus.on("FIELD_CHANGED", this, (ev) => {
            if (ev.data.changes && ev.data.changes.hasOwnProperty('current_quarter')) {
                const quarterValue = ev.data.changes.current_quarter;
                this.switchToQuarterTab(quarterValue);
            }
        });
        
        // При загрузке формы проверяем значение current_quarter и переключаем вкладку
        if (this.model.root && this.model.root.data && this.model.root.data.current_quarter) {
            // Ждем, пока форма загрузится
            setTimeout(() => {
                this.switchToQuarterTab(this.model.root.data.current_quarter);
            }, 100);
        }
    }
    
    /**
     * Переключает активную вкладку в соответствии с выбранной четвертью
     * @param {string} quarterValue - Значение четверти (1, 2, 3 или 4)
     */
    switchToQuarterTab(quarterValue) {
        // Находим элемент notebook (вкладки)
        const notebook = document.querySelector('.o_form_sheet .o_notebook');
        if (notebook) {
            // Находим все вкладки
            const tabs = notebook.querySelectorAll('.nav-tabs .nav-link');
            if (tabs.length >= parseInt(quarterValue)) {
                // Активируем соответствующую вкладку (индекс на 1 меньше значения четверти)
                const tabIndex = parseInt(quarterValue) - 1;
                if (tabs[tabIndex] && !tabs[tabIndex].classList.contains('active')) {
                    tabs[tabIndex].click();
                }
            }
        }
    }
}

// Регистрируем наш контроллер
registry.category("views").add("subject_grades_form", {
    ...formView,
    Controller: SubjectGradesFormController,
});