/**
 * Кнопки оценки ДЗ — ПК-версия кружков миниаппа (JournalButton, 2026-10).
 *
 * Поле marks/marks_2 — Float, в ПК его вводили вручную числом. Теперь тап
 * по кружку записывает значение: у непринятой работы оценка выбирается и
 * сохраняется штатно по Save формы; повторный тап по тому же кружку
 * сбрасывает («—»), как довод цикла «— → 5 → 4 → 3 → 2 → —» в миниаппе.
 *
 * Цвета — те же, что утверждены для JournalButton (единый словарь):
 * 5 зелёный, 4 синий, 3 янтарный, 2 красный, «—» нейтральный.
 * В веб-клиенте Odoo есть свои bs-варианты с тем же смыслом
 * (success/primary/warning/danger), они темизируются сами — своего CSS нет.
 *
 * Виджет работает и в form, и в list (supportedTypes: float). В
 * readonly (ученик, принятая работа) кружки не кликаются.
 */
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

const GRADES = [5, 4, 3, 2];

/** bs-класс залитого кружка по оценке. */
const filledClass = (n) => {
    switch (n) {
        case 5: return "btn-success";
        case 4: return "btn-primary";
        case 3: return "btn-warning";
        case 2: return "btn-danger";
        default: return "btn-outline-secondary";
    }
};

/** bs-класс контурного кружка того же цвета. */
const outlineClass = (n) => {
    switch (n) {
        case 5: return "btn-outline-success";
        case 4: return "btn-outline-primary";
        case 3: return "btn-outline-warning";
        case 2: return "btn-outline-danger";
        default: return "btn-outline-secondary";
    }
};

export class HwMarksField extends Component {
    static template = "rost_lesson_homework.HwMarksField";
    static props = { ...standardFieldProps };

    /** Float в кружках — целые 2..5; 0/пусто = «—». */
    get value() {
        const v = this.props.record.data[this.props.name];
        return v ? Math.round(v) : null;
    }

    /** Тап по кружку N: то же значение — обнулить, другое — записать. */
    pick(n) {
        if (this.props.readonly) return;
        const v = this.value === n ? null : n;
        this.props.record.update({ [this.props.name]: v });
    }
}

export const hwMarksField = {
    component: HwMarksField,
    supportedTypes: ["float"],
    extractProps: () => ({}),
};

registry.category("fields").add("hw_marks", hwMarksField);
