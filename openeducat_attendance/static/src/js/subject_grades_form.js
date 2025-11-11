/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onWillRender } from "@odoo/owl";

export class SubjectGradesFormController extends FormController {
    setup() {
        super.setup();
        
        // Отслеживаем изменение значения поля current_quarter
        let previousQuarter = null;
        
        // При загрузке формы проверяем значение current_quarter и переключаем вкладку
        onWillRender(() => {
            if (this.model && this.model.root && this.model.root.data && this.model.root.data.current_quarter) {
                const currentQuarter = this.model.root.data.current_quarter;
                if (currentQuarter !== previousQuarter) {
                    previousQuarter = currentQuarter;
                    // Ждем, пока форма загрузится
                    setTimeout(() => {
                        this.switchToQuarterTab(currentQuarter);
                    }, 100);
                }
            }
        });
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