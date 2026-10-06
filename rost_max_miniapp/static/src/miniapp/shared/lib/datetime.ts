/**
 * Даты сервера и их отображение — ЕДИНСТВЕННОЕ место для всего миниаппа.
 *
 * Контракт: Odoo хранит datetime в наивном UTC («2026-10-06 07:45:13»).
 * JS Date без флага UTC трактует такую строку как локальное время —
 * из-за этого время показывалось на зону раньше/позже (подписи «сдал
 * сегодня в …» показывали сырую UTC). Правило: ЛЮБАЯ серверная строка
 * парсится только через parseServerDate; отображение — время устройства
 * (Date сам переводит UTC → локальную зону), как в мессенджерах.
 *
 * Пользователи: HwChat (лента чата), ReviewQueue (очередь проверки),
 * HomeworkCardList (карточки ДЗ). Новый форматтер — добавлять здесь,
 * а не в компоненте.
 */

/** Названия месяцев (родительный падеж для «12 окт»). */
export const MONTHS = [
  'янв', 'фев', 'мар', 'апр', 'мая', 'июн',
  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек',
];

/**
 * Серверная строка -> Date. Наивные datetime-строки считаются UTC
 * (добавляем 'Z'); date-only строки («2026-10-06») — UTC-полночь, чтобы
 * календарный день не уехал в предыдущий. Невалидная строка -> null.
 */
export const parseServerDate = (iso: string | null | undefined): Date | null => {
  if (!iso) return null;
  const s = String(iso).trim();
  if (!s) return null;
  // date-only («2026-10-06») — UTC-полночь.
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(s);
  const js = dateOnly ? `${s}T00:00:00Z` : s.replace(' ', 'T') + 'Z';
  const d = new Date(js);
  return isNaN(d.getTime()) ? null : d;
};

const pad = (n: number): string => String(n).padStart(2, '0');

/** Время устройства «15:45». */
export const fmtTime = (d: Date): string => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

/** Сравнение по календарному дню в локальной зоне. */
export const isSameDay = (a: Date, b: Date): boolean =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

/** «Сегодня» / «Вчера» / «12 окт» по календарному дню. */
export const fmtDayName = (d: Date): string => {
  const now = new Date();
  if (isSameDay(d, now)) return 'Сегодня';
  const yest = new Date(now);
  yest.setDate(now.getDate() - 1);
  if (isSameDay(d, yest)) return 'Вчера';
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
};

/**
 * «сдал сегодня в 15:45» / «сдал вчера в 15:45» / «сдал 12 окт».
 * withPrefix=false — без слова «сдал» («сегодня в 15:45»): подпись
 * принятой работы в очереди проверки.
 */
export const fmtSubmitted = (iso: string, withPrefix = true): string => {
  const d = parseServerDate(iso);
  if (!d) return '';
  const now = new Date();
  const yest = new Date(now);
  yest.setDate(now.getDate() - 1);
  const day = isSameDay(d, now) ? 'сегодня'
    : isSameDay(d, yest) ? 'вчера'
      : `${d.getDate()} ${MONTHS[d.getMonth()]}`;
  const dayPart = withPrefix ? `сдал ${day}` : day;
  const hh = d.getHours();
  const mm = d.getMinutes();
  return (hh || mm) ? `${dayPart} в ${fmtTime(d)}` : dayPart;
};

/**
 * Дедлайн сдачи «до 12 окт к 18:00» (дата-время) или «до 12 окт»
 * (date-only: полночь UTC не «к 03:00», время не показываем).
 */
export const fmtDue = (iso: string): string => {
  const d = parseServerDate(iso);
  if (!d) return '';
  const hasTime = !/^\d{4}-\d{2}-\d{2}$/.test(String(iso).trim());
  const timePart = hasTime ? ` к ${fmtTime(d)}` : '';
  return `до ${d.getDate()} ${MONTHS[d.getMonth()]}${timePart}`;
};

/** Дата выдачи «12 сен». */
export const fmtIssued = (iso: string): string => {
  const d = parseServerDate(iso);
  if (!d) return '';
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
};

/**
 * Разделитель дня в ленте чата: «Сегодня, 18:42» / «Вчера, 09:10» /
 * «12 окт, 19:00».
 */
export const fmtDayWithTime = (d: Date): string => `${fmtDayName(d)}, ${fmtTime(d)}`;