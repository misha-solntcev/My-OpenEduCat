/**
 * Нумерация уроков дня.
 *
 * Урок дня — это СЛОТ из сетки звонков («09:30 - 10:10»), а не строка
 * списка. В одном слоте может стоять несколько уроков одного класса —
 * группы английского (А/Б), элективы, профильные пары. Для школы это
 * один и тот же урок дня, поэтому номер у них общий.
 *
 * Раньше номер рисовался как позиция строки (`i + 1`): класс с двумя
 * группами английского видел «5-й» и «6-й» урок в одном слоте, а в
 * заголовке ленты — «6 уроков» вместо 5.
 *
 * Порядок входа — как отдал сервер (op.session order: start_datetime
 * asc); номера идут по первому появлению слота.
 */

/** Ключ слота: строка тайминга. Пустой тайминг — не слот, у строки свой номер. */
const slotKey = (timing: string | undefined, index: number): string =>
  timing && timing.trim() ? timing.trim() : `#${index}`;

/** Номер урока для каждой строки списка (1..N по слотам). */
export const daySlotNumbers = <T extends { timing: string }>(
  lessons: T[],
): number[] => {
  const bySlot = new Map<string, number>();
  return lessons.map((l, i) => {
    const key = slotKey(l.timing, i);
    let num = bySlot.get(key);
    if (num == null) {
      num = bySlot.size + 1;
      bySlot.set(key, num);
    }
    return num;
  });
};

/** Сколько уроков в дне: слоты, а не строки (параллельные — один урок). */
export const daySlotCount = <T extends { timing: string }>(
  lessons: T[],
): number => new Set(daySlotNumbers(lessons)).size;

/**
 * Номера уроков для рельса. Приоритет — номер пары из API (сетка звонков
 * op.timing: если первого урока в дне нет, урок в 10:20 так и остаётся
 * вторым — LIN-6). Уроков без номера (не привязан к сетке) нумеруем по
 * слотам дня, чтобы в рельсе не было пропусков.
 */
export const lessonNumbers = <T extends { timing: string; num?: number | null }>(
  lessons: T[],
): number[] => {
  const fallback = daySlotNumbers(lessons);
  return lessons.map((l, i) => (l.num != null ? l.num : fallback[i]));
};
