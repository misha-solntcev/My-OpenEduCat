/**
 * Единая точка правды для фильтров расписания (дата + преподаватель).
 *
 * Дата хранится только в памяти и всегда стартует с «сегодня по школе»
 * (Europe/Moscow). Персистить её не нужно: сохранённая дата приводила к
 * тому, что приложение открывалось на произвольном дне прошлой навигации
 * (sessionStorage в WebView живёт дольше, чем кажется).
 */

import { schoolTodayISO } from './date';

export interface TimetableFilters {
  date: string;
  selectedFaculty: number | null;
  selectedBatch: number | null;
}

/** Сегодняшняя дата школы (Europe/Moscow), не UTC: миниапп открывают
 * из других часовых поясов, toISOString() отстаёт на день до 07:00 Иркутска. */
export function today(): string {
  return schoolTodayISO();
}

export function getSavedFilters(): TimetableFilters {
  return {
    date: today(),
    selectedFaculty: null,
    selectedBatch: null,
  };
}

export function saveFilters(_patch: Partial<TimetableFilters>): void {
  // Персистенции больше нет — дата всегда сегодня, фильтры живут в памяти.
}
