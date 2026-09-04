/** Утилиты дат: локальная зона устройства, без TZ-сдвигов. */

/** Локальная дата -> 'YYYY-MM-DD' без TZ-сдвига. */
export const toISO = (d: Date): string => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

/** Понедельник недели, содержащей d. */
export const startOfWeek = (d: Date): Date => {
  const date = new Date(d);
  const day = (date.getDay() + 6) % 7; // 0=пн ... 6=вс
  date.setDate(date.getDate() - day);
  date.setHours(0, 0, 0, 0);
  return date;
};

/** Короткие имена дней недели, пн -> вс. */
export const SHORT_WEEKDAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'];
