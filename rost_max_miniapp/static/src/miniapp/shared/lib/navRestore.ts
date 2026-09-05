// Восстановление навигации SPA после перезапуска WebView (звонок, refresh,
// возврат из фона). Пишем в sessionStorage при каждом переходе, читаем
// синхронно при бутстрапе — юзер возвращается на тот экран, где был.

import type { TabId } from '@/shared/lib/navTypes';

const KEY = 'rost_max_nav';

export interface NavState {
  view: 'main' | 'lesson-journal';
  tab: TabId;
  timetableHistory: string[];
  subjectsHistory: string[];
  selectedLessonId: number | null;
  selectedSubject: { id: number; name: string } | null;
}

export function loadNavState(): Partial<NavState> {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Partial<NavState>) : {};
  } catch {
    return {};
  }
}

export function saveNavState(state: NavState): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // sessionStorage недоступен — навигация просто не восстановится
  }
}

export function clearNavState(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // игнорируем
  }
}
