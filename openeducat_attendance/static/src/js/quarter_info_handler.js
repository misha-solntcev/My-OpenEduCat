/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { onWillRender, onMounted } from "@odoo/owl";

export class QuarterInfoFormController extends FormController {
    setup() {
        super.setup();
        
        let updateTimeout = null;
        
        // Отслеживаем изменение активной вкладки
        onWillRender(() => {
            // Очищаем предыдущий таймер
            if (updateTimeout) {
                clearTimeout(updateTimeout);
            }
            
            // Ждем немного, чтобы DOM обновился
            updateTimeout = setTimeout(() => {
                this.updateQuarterInfo();
            }, 150);
        });
        
        // Обновляем информацию при монтировании компонента
        onMounted(() => {
            // Добавляем обработчик событий для переключения вкладок
            this.addTabChangeListener();
            
            setTimeout(() => {
                this.updateQuarterInfo();
            }, 300);
        });
    }
    
    /**
     * Добавляет обработчик событий для переключения вкладок
     */
    addTabChangeListener() {
        // Ждем, пока вкладки будут загружены
        setTimeout(() => {
            const tabs = document.querySelectorAll('.o_form_sheet .nav-tabs .nav-link');
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    // Ждем, пока вкладка будет активирована
                    setTimeout(() => {
                        this.updateQuarterInfo();
                    }, 100);
                });
            });
        }, 500);
    }
    
    /**
     * Обновляет отображение информации по выбранной четверти
     */
    updateQuarterInfo() {
        // Находим активную вкладку
        const activeTab = document.querySelector('.o_form_sheet .nav-tabs .nav-link.active');
        if (activeTab) {
            const tabText = activeTab.textContent.trim();
            let quarter = 0;
            
            // Определяем номер четверти по тексту вкладки
            if (tabText.includes('1')) {
                quarter = 1;
            } else if (tabText.includes('2')) {
                quarter = 2;
            } else if (tabText.includes('3')) {
                quarter = 3;
            } else if (tabText.includes('4')) {
                quarter = 4;
            }
            
            // Если определили четверть, обновляем информацию
            if (quarter > 0) {
                this.updateInfoFields(quarter);
            }
        }
    }
    
    /**
     * Обновляет поля информации в соответствии с выбранной четвертью
     * @param {number} quarter - Номер четверти (1-4)
     */
    updateInfoFields(quarter) {
        // Получаем данные из соответствующих скрытых полей
        const totalClassesField = document.querySelector(`.o_field_widget[name="q${quarter}_total_classes"]`);
        const presentClassesField = document.querySelector(`.o_field_widget[name="q${quarter}_present_classes"]`);
        const lastAttendanceDateField = document.querySelector(`.o_field_widget[name="q${quarter}_last_attendance_date"]`);
        const averageMarkField = document.querySelector(`.o_field_widget[name="q${quarter}_average_mark"]`);
        
        // Находим поля для отображения информации
        const displayTotalClasses = document.querySelector('.quarter-info-total-classes span');
        const displayPresentClasses = document.querySelector('.quarter-info-present-classes span');
        const displayLastAttendanceDate = document.querySelector('.quarter-info-last-attendance-date span');
        const displayAverageMark = document.querySelector('.quarter-info-average-mark span');
        
        // Обновляем отображение
        if (totalClassesField && displayTotalClasses) {
            displayTotalClasses.textContent = totalClassesField.textContent || '0';
        }
        
        if (presentClassesField && displayPresentClasses) {
            displayPresentClasses.textContent = presentClassesField.textContent || '0';
        }
        
        if (lastAttendanceDateField && displayLastAttendanceDate) {
            displayLastAttendanceDate.textContent = lastAttendanceDateField.textContent || '';
        }
        
        if (averageMarkField && displayAverageMark) {
            // Форматируем среднюю оценку до 2 знаков после запятой
            const avgMark = parseFloat(averageMarkField.textContent);
            if (!isNaN(avgMark)) {
                displayAverageMark.textContent = avgMark.toFixed(2);
            } else {
                displayAverageMark.textContent = '0.00';
            }
        }
    }
}

// Регистрируем наш контроллер
registry.category("views").add("quarter_info_form", {
    ...formView,
    Controller: QuarterInfoFormController,
});