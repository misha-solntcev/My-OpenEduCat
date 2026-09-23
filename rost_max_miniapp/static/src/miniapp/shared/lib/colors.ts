import type { GradeField } from './types';

// Метаданные колонок оценок журнала.
// Цвета оценок/посещаемости — через VKUI Button appearance, см. cycle.ts.

export const GRADE_FIELDS: GradeField[] = ['grade_1', 'grade_2', 'hw_grade_1', 'hw_grade_2'];

// Подписи кнопок-оценок: урок — «О1/О2», домашка — «ДЗ 1/ДЗ 2».
export const GRADE_LABELS: Record<GradeField, string> = {
  grade_1: 'О1',
  grade_2: 'О2',
  hw_grade_1: 'ДЗ 1',
  hw_grade_2: 'ДЗ 2',
};

// Цикл оценок: пусто → 5 → 4 → 3 → 2 → пусто
export const GRADES = ['', '5', '4', '3', '2'] as const;
