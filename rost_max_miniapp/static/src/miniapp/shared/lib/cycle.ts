import type { AttendanceType } from './types';
import { GRADES } from './colors';

/** Внешний вид кнопки по цветовой карте Миши (2026-09-15):
 *  positive = зелёный, accent = синий, warning = янтарный, negative = красный. */
export type GradeAppearance = 'positive' | 'accent' | 'warning' | 'negative';

/** Оценки: 5 зелёная, 4 синяя, 3 янтарная, 2 красная. */
export function getGradeAppearance(grade: number | null | undefined): GradeAppearance {
  if (grade == null) return 'positive';
  if (grade >= 5) return 'positive';
  if (grade >= 4) return 'accent';
  if (grade >= 3) return 'warning';
  return 'negative';
}

/** Посещаемость по названию типа:
 *  присутствовал/дистанционно — зелёный, опоздание — синий,
 *  болеет/уважительная — янтарный, прогул — красный. */
export function getAttendanceAppearance(name?: string): GradeAppearance {
  if (!name) return 'positive';
  const n = name.toLowerCase();
  // «Опоздал» раньше «присутствовал»: подстрока «да» ловится и там и там.
  if (n.includes('опоздал') || n.includes('опоздание')) return 'accent';
  if (n.includes('прогул')) return 'negative';
  if (n.includes('болеет') || n.includes('болезнь')) return 'warning';
  if (n.includes('уважит')) return 'warning';
  if (n.includes('дистанц')) return 'positive';
  if (n.includes('присутств') || n.includes('был') || n.includes('есть')) return 'positive';
  return 'positive'; // неизвестный тип считаем присутствием (норма)
}

/** Цикл оценок: пусто → 5 → 4 → 3 → 2 → пусто */
export function cycleGrade(current: number | null): number | null {
  const currentStr = current != null ? String(current) : '';
  const idx = GRADES.indexOf(currentStr as '' | '2' | '3' | '4' | '5');
  const nextRaw = GRADES[(idx + 1) % GRADES.length];
  return nextRaw === '' ? null : Number(nextRaw);
}

/** Цикл посещаемости: — → тип1 → … → типN → — (замыкается на пусто).
 *  Раньше из пустого выходили в тип1, но возврата в «—» не было —
 *  пустое состояние нельзя было поставить обратно тапом. */
export function cycleAttendance(current: number | null, types: AttendanceType[]): number | null {
  if (types.length === 0) return null;
  if (current == null) return types[0].id;
  const curIdx = types.findIndex(t => t.id === current);
  if (curIdx === types.length - 1) return null;  // последний тип → назад в «—»
  return types[curIdx + 1].id;
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
