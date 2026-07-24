// Цвета оценок и посещаемости + метаданные колонок.
// Выделено из LessonJournalPage, т.к. используется и в строке студента
// (StudentRow), и в массовой сетке шторки.

import type { GradeField } from './types';

export const GRADE_FIELDS: GradeField[] = ['grade_1', 'grade_2', 'grade_3'];
export const GRADE_FIELD_LABELS: Record<GradeField, string> = {
  grade_1: 'О1',
  grade_2: 'О2',
  grade_3: 'О3',
};

// Цикл оценок: пусто → 5 → 4 → 3 → 2 → пусто
export const GRADES = ['', '5', '4', '3', '2'];

// Цвет отметки посещаемости по названию типа
export function attendanceColor(name?: string): string {
  if (!name) return 'var(--text-secondary)';
  const n = name.toLowerCase();
  if (n.includes('присутств') || n.includes('был') || n.includes('есть') || n.includes('да')) return 'var(--background-accent-positive)';
  if (n.includes('отсутств') || n.includes('нет') || n.includes('не ')) return 'var(--background-accent-negative)';
  if (n.includes('опозд')) return 'var(--background-accent-attention-primary)';
  return 'var(--icon-themed)';
}

export function gradeColor(grade: number | null): string {
  if (grade == null) return 'var(--text-secondary)';
  if (grade >= 3.5) return 'var(--background-accent-positive)';
  if (grade >= 2.5) return 'var(--background-accent-attention-primary)';
  return 'var(--background-accent-negative)';
}