import type { AttendanceType } from './types';
import { GRADES } from './colors';

/** Цикл оценок: пусто → 5 → 4 → 3 → 2 → пусто */
export function cycleGrade(current: number | null): number | null {
  const currentStr = current != null ? String(current) : '';
  const idx = GRADES.indexOf(currentStr as '' | '2' | '3' | '4' | '5');
  const nextRaw = GRADES[(idx + 1) % GRADES.length];
  return nextRaw === '' ? null : Number(nextRaw);
}

/** Цикл посещаемости по списку типов */
export function cycleAttendance(current: number | null, types: AttendanceType[]): number | null {
  if (types.length === 0) return null;
  const curIdx = types.findIndex(t => t.id === current);
  const nextType = types[(curIdx + 1) % types.length];
  return nextType.id;
}

/** Отображаемое значение оценки */
export function getGradeDisplay(value: number | null): string {
  return value != null ? String(value) : '—';
}

/** Отображаемое значение посещаемости */
export function getAttendanceDisplay(value: number | null, types: AttendanceType[]): string {
  if (value == null) return '—';
  const found = types.find(t => t.id === value);
  return found?.name ?? '—';
}

/** Цвет оценки */
export function getGradeColor(grade: number | null): string {
  if (grade == null) return 'var(--text-secondary)';
  if (grade >= 3.5) return 'var(--background-accent-positive)';
  if (grade >= 2.5) return 'var(--background-accent-attention-primary)';
  return 'var(--background-accent-negative)';
}

/** Цвет посещаемости по названию типа */
export function getAttendanceColor(name?: string): string {
  if (!name) return 'var(--text-secondary)';
  const n = name.toLowerCase();
  if (n.includes('присутств') || n.includes('был') || n.includes('есть') || n.includes('да')) {
    return 'var(--background-accent-positive)';
  }
  if (n.includes('отсутств') || n.includes('нет') || n.includes('не ')) {
    return 'var(--background-accent-negative)';
  }
  if (n.includes('опозд')) {
    return 'var(--background-accent-attention-primary)';
  }
  return 'var(--icon-themed)';
}