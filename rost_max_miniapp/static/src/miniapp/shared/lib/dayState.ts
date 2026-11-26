/**
 * Состояние учебного дня по строкам рельса (уроки + пустые пары).
 *
 * Вынесено из ленты главной (`TodayTimeline`), чтобы расписание считало
 * ТО ЖЕ состояние теми же правилами: «до уроков», «идёт урок», «перемена»,
 * «обед», «всё завершено». До выноса расписание знало только «идёт урок»,
 * и в перемену на нём не было подсвечено вообще ничего (жалоба Миши
 * 26.11.2026: «на главной работает, а в расписании нет»).
 *
 * Пустые пары (`lesson === null`) тоже участвуют: «перемена» и «сейчас»
 * считаются по строкам, а не по урокам.
 */

import { timingToMinutes } from '@/shared/components/timelinePrimitives';
import type { DayRow } from '@/shared/lib/slots';

export type DayPhase = 'before' | 'lesson' | 'break' | 'after';

export interface DayState {
  phase: DayPhase;
  /** Индекс слота: текущего (lesson) или следующего (break/before). */
  slotIndex: number;
  /** Процент прошлого этапа прогресса (0..100). */
  progress: number;
  /** Минут до начала ближайшего события (перемена/до уроков). */
  minutesLeft: number;
  /** Длина перемены в минутах. */
  breakTotal: number;
}

/** Состояние дня из строк рельса (уроки + пустые слоты): «перемена» и
 *  «сейчас» работают и на пустых парах. Пустой день — null. */
export const computeDayState = <T>(
  rows: DayRow<T>[],
  nowMin: number,
): DayState | null => {
  const timed = rows
    .map((r, i) => ({ i, isLesson: Boolean(r.lesson), range: timingToMinutes(r.timing) }))
    .filter((s): s is { i: number; isLesson: boolean; range: [number, number] } => s.range != null);
  if (!timed.length) return null;

  for (let k = 0; k < timed.length; k++) {
    const { i, isLesson, range } = timed[k];
    const [start, end] = range;
    if (nowMin < start) {
      // До первого урока или перемена перед слотом.
      if (k === 0) {
        return {
          phase: 'before', slotIndex: i, progress: 0,
          minutesLeft: start - nowMin, breakTotal: 0,
        };
      }
      const prevEnd = timed[k - 1].range[1];
      const total = start - prevEnd;
      return {
        phase: 'break', slotIndex: i, progress: 0,
        minutesLeft: start - nowMin, breakTotal: total,
      };
    }
    if (nowMin < end) {
      const progress = Math.round(((nowMin - start) / (end - start)) * 100);
      // Пустой слот идёт сейчас — это не урок, а окно: показываем
      // «перемену» с остатком до конца пары.
      return isLesson
        ? { phase: 'lesson', slotIndex: i, progress, minutesLeft: 0, breakTotal: 0 }
        : { phase: 'break', slotIndex: i, progress, minutesLeft: end - nowMin, breakTotal: 0 };
    }
  }
  return { phase: 'after', slotIndex: rows.length - 1, progress: 100, minutesLeft: 0, breakTotal: 0 };
};
