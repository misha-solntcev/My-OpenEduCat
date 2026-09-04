/** Утилиты дат. Школа в Europe/Moscow (UTC+3, без перехода на летнее
 * время) — «сейчас» и «сегодня» считаем по школьной зоне, а не по зоне
 * устройства: миниапп открывают из других часовых поясов. */

/** Смещение школьной зоны: минуты от UTC. */
export const SCHOOL_TZ_OFFSET_MIN = 180; // Europe/Moscow, UTC+3

/** «Сейчас» по школьному времени (минуты от полуночи школьного дня). */
export const schoolNowMinutes = (): number => {
  const utc = Date.now();
  const shifted = new Date(utc + SCHOOL_TZ_OFFSET_MIN * 60000);
  return shifted.getUTCHours() * 60 + shifted.getUTCMinutes();
};

/** Сегодняшняя дата школы в формате 'YYYY-MM-DD'. */
export const schoolTodayISO = (): string => {
  const shifted = new Date(Date.now() + SCHOOL_TZ_OFFSET_MIN * 60000);
  const y = shifted.getUTCFullYear();
  const m = String(shifted.getUTCMonth() + 1).padStart(2, '0');
  const day = String(shifted.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

/** Локальная дата -> 'YYYY-MM-DD' (для дат, выбранных в календаре). */
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
