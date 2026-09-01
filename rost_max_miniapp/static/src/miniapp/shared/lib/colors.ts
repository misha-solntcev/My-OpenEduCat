import type { GradeField } from './types';

// Метаданные колонок оценок журнала.
// Цвета оценок/посещаемости — через VKUI Button appearance, см. cycle.ts.

export const GRADE_FIELDS: GradeField[] = ['grade_1', 'grade_2', 'grade_3'];

// Цикл оценок: пусто → 5 → 4 → 3 → 2 → пусто
export const GRADES = ['', '5', '4', '3', '2'] as const;
