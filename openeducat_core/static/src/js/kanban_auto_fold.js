/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { patch } from "@web/core/utils/patch";
import { onRendered } from "@odoo/owl";

patch(KanbanRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        
        this.isAutoFolding = false;
        // Хранилище для отслеживания последнего известного количества записей в группах
        // { group_id: last_count }
        this.lastGroupCounts = new Map();

        onRendered(() => {
            const list = this.props.list;
            
            if (!list || !["op.attendance.sheet", "op.session"].includes(list.resModel) || this.isAutoFolding) {
                return;
            }

            const groupsToProcess = [];

            for (const group of list.groups) {
                const currentCount = group.list.count;
                const groupId = group.value; // Используем значение группы (день недели) как ключ
                const lastCount = this.lastGroupCounts.get(groupId);

                // ЛОГИКА:
                // Мы вмешиваемся только если:
                // 1. Мы первый раз видим эту группу (lastCount === undefined)
                // 2. Количество записей в группе изменилось (например, сработал фильтр)
                if (lastCount === undefined || lastCount !== currentCount) {
                    const shouldBeFolded = currentCount === 0;
                    
                    if (group.isFolded !== shouldBeFolded) {
                        groupsToProcess.push(group);
                    }
                    // Запоминаем новое количество
                    this.lastGroupCounts.set(groupId, currentCount);
                }
                
                // Если lastCount === currentCount, значит данные не менялись.
                // Если при этом состояние group.isFolded изменилось — это сделал пользователь вручную.
                // Мы не добавляем такую группу в groupsToProcess, позволяя ей остаться в выбранном состоянии.
            }

            if (groupsToProcess.length > 0) {
                this.isAutoFolding = true;
                setTimeout(async () => {
                    try {
                        for (const group of groupsToProcess) {
                            // Еще раз проверяем, нужно ли переключать (защита от гонки состояний)
                            const shouldBeFolded = group.list.count === 0;
                            if (group.isFolded !== shouldBeFolded) {
                                await group.toggle();
                            }
                        }
                    } finally {
                        this.isAutoFolding = false;
                    }
                }, 0);
            }
        });
    },
});