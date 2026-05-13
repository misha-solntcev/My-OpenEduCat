/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { patch } from "@web/core/utils/patch";
import { onRendered } from "@odoo/owl";

patch(KanbanRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        
        // Флаг-предохранитель, чтобы избежать бесконечного цикла
        this.isAutoFolding = false;

        onRendered(() => {
            const list = this.props.list;
            
            // Проверяем модель и наличие блокировки
            if (!list || !["op.attendance.sheet", "op.session"].includes(list.resModel) || this.isAutoFolding) {
                return;
            }

            // Ищем группы, состояние которых не соответствует количеству записей
            const groupsToProcess = list.groups.filter(group => {
                const shouldBeFolded = group.list.count === 0;
                return group.isFolded !== shouldBeFolded;
            });

            // Если такие группы есть, запускаем процесс переключения
            if (groupsToProcess.length > 0) {
                this.isAutoFolding = true; // Ставим блокировку

                // Выносим в микрозадачу, чтобы выйти из текущего цикла отрисовки Owl
                setTimeout(async () => {
                    try {
                        for (const group of groupsToProcess) {
                            // Проверяем условие еще раз непосредственно перед вызовом
                            const currentShouldBeFolded = group.list.count === 0;
                            if (group.isFolded !== currentShouldBeFolded) {
                                await group.toggle();
                            }
                        }
                    } finally {
                        // Снимаем блокировку только после того, как ВСЕ группы обработаны
                        this.isAutoFolding = false;
                    }
                }, 0);
            }
        });
    },
});