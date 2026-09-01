import type { AttendanceType } from './types';
import { GRADES } from './colors';

/** Appearance VKUI Button по целой оценке (2..5, дробных нет —
 * дробными бывают только средние): 5/4 зелёная, 3 нейтральная, 2 красная. */
export type GradeAppearance = 'positive' | 'neutral' | 'negative';

export function getGradeAppearance(grade: number | null | undefined): GradeAppearance {
  if (grade == null) return 'neutral';
  if (grade >= 4) return 'positive';
  if (grade >= 3) return 'neutral';
  return 'negative';
}

/** Appearance по названию типа посещаемости:
 * присутствовал — зелёный, опоздание — нейтральный, отсутствие — красный. */
export function getAttendanceAppearance(name?: string): GradeAppearance {
  if (!name) return 'neutral';
  const n = name.toLowerCase();
  if (n.includes('присутств') || n.includes('был') || n.includes('есть') || n.includes('да')) {
    return 'positive';
  }
  if (n.includes('отсутств') || n.includes('нет') || n.includes('не ')) {
    return 'negative';
  }
  return 'neutral'; // опоздание и прочее
}

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
