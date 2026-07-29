/**
 * Единая точка правды для фильтров расписания (дата + преподаватель).
 *
 * Раньше логика чтения/записи sessionStorage дублировалась в App.tsx и
 * TimetablePage.tsx двумя разными способами: App делал MERGE, TimetablePage —
 * ПОЛНУЮ перезапись. Это хрупко: правишь форму хранения в одном месте,
 * забываешь в другом — фильтры ломаются. Теперь один модуль.
 *
 * saveFilters принимает Partial и мержит с текущим объектом, чтобы писатели
 * из разных экранов не затирали чужие поля (date глобальный, faculty локальный).
 */

const FILTERS_KEY = 'rost_max_timetable_filters';

export interface TimetableFilters {
  date: string;
  selectedFaculty: number | null;
}

export function today(): string {
  return new Date().toISOString().split('T')[0];
}

export function getSavedFilters(): TimetableFilters {
  const fallback: TimetableFilters = { date: today(), selectedFaculty: null };
  try {
    const saved = sessionStorage.getItem(FILTERS_KEY);
    if (!saved) return fallback;
    const parsed = JSON.parse(saved);
    return {
      date: typeof parsed.date === 'string' && parsed.date ? parsed.date : fallback.date,
      selectedFaculty:
        parsed.selectedFaculty === undefined || parsed.selectedFaculty === null
          ? null
          : Number(parsed.selectedFaculty),
    };
  } catch {
    // sessionStorage недоступен (приватный режим) — возвращаем дефолт
    return fallback;
  }
}

export function saveFilters(patch: Partial<TimetableFilters>): void {
  try {
    const current = getSavedFilters();
    sessionStorage.setItem(FILTERS_KEY, JSON.stringify({ ...current, ...patch }));
  } catch {
    // sessionStorage недоступен — игнорируем
  }
}
