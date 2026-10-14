import { create } from 'zustand';
import { apiGet, hasSavedSession } from './api';
import { loadThemePreference, saveThemePreference, type ThemePreference } from './theme';
import type { UserInfo } from './types';

// Режим «ребёнок» (переключатель «Мои уроки / Ребёнок»): id выбранного
// op.student живёт в sessionStorage — переживает перезапуск WebView
// (звонок, сворачивание), как тема. При логине другого юзера
// сохранённый id валидируется в loadUserInfo по списку детей и затирается.
const CHILD_KEY = 'rost_max_child_id';
// Режим «Школа» админа (свитч «Мои уроки / Школа / Ребёнок»): по умолчанию
// у staff выбран «Мои уроки», «Школа» — явный выбор, переживает рестарт.
const SCHOOL_KEY = 'rost_max_school';

function loadChildId(): number | null {
  try {
    const raw = sessionStorage.getItem(CHILD_KEY);
    const n = raw ? Number(raw) : NaN;
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

function saveChildId(id: number | null): void {
  try {
    if (id == null) sessionStorage.removeItem(CHILD_KEY);
    else sessionStorage.setItem(CHILD_KEY, String(id));
  } catch {
    // sessionStorage недоступен — режим просто не переживёт рестарт
  }
}

function loadSchoolMode(): boolean {
  try {
    return sessionStorage.getItem(SCHOOL_KEY) === '1';
  } catch {
    return false;
  }
}

function saveSchoolMode(on: boolean): void {
  try {
    if (on) sessionStorage.setItem(SCHOOL_KEY, '1');
    else sessionStorage.removeItem(SCHOOL_KEY);
  } catch {
    // игнорируем
  }
}

/** Хвост query-string для «ученических» эндпоинтов в режиме ребёнка:
 *  '&child_id=N' или '' — вызов append-ом к готовому URL. */
export function childQuery(): string {
  const id = useAppStore.getState().selectedChildId;
  return id != null ? `&child_id=${id}` : '';
}

/** scope для timetable/dashboard_info у staff (teacher/admin):
 *  'mine' по умолчанию, 'school' — явный выбор админа. В режиме ребёнка
 *  scope не нужен. У не-staff — ''. */
export function scopeQuery(): string {
  const s = useAppStore.getState();
  const isStaff = Boolean(s.userInfo?.is_teacher || s.userInfo?.is_admin);
  if (!isStaff || s.selectedChildId != null) return '';
  return s.schoolMode ? '&scope=school' : '&scope=mine';
}

interface AppState {
  // Профиль и роли
  userInfo: UserInfo | null;
  loadUserInfo: () => Promise<void>;

  // Флаг успешного логина — триггерит переход login -> main
  authSuccess: boolean;
  setAuthSuccess: (v: boolean) => void;

  // Идёт проверка сохранённой сессии при загрузке страницы (restart WebView,
  // refresh, возврат из фона): показываем спиннер вместо экрана логина,
  // чтобы он не мигал на время запроса /api/user/info.
  authChecking: boolean;
  setAuthChecking: (v: boolean) => void;

  // Тема: light / dark / system. Читается из localStorage синхронно при
  // создании стора — первый кадр уже с выбранной темой, без мигания.
  themePreference: ThemePreference;
  setThemePreference: (pref: ThemePreference) => void;

  // Режим «ребёнок»: null — свои данные, иначе id ребёнка.
  selectedChildId: number | null;
  setChildId: (id: number | null) => void;

  // Режим «Школа» (свитч админа-родителя): false — «Мои уроки» (дефолт).
  schoolMode: boolean;
  setSchoolMode: (on: boolean) => void;
}

// Хранилище (создаём сначала)
const useAppStore = create<AppState>((set, get) => ({
  userInfo: null,
  authSuccess: false,
  // Синхронно до первого рендера: если есть сохранённый sid, первый кадр —
  // уже спиннер проверки, форма логина не рисуется вовсе (иначе useEffect
  // срабатывает после первого рендера и логин мигает на ~1 кадр).
  authChecking: hasSavedSession(),
  setAuthSuccess: (v: boolean) => set({ authSuccess: v }),
  setAuthChecking: (v: boolean) => set({ authChecking: v }),
  themePreference: loadThemePreference(),
  setThemePreference: (pref: ThemePreference) => {
    saveThemePreference(pref);
    set({ themePreference: pref });
  },
  selectedChildId: loadChildId(),
  setChildId: (id: number | null) => {
    saveChildId(id);
    set({ selectedChildId: id });
  },
  schoolMode: loadSchoolMode(),
  setSchoolMode: (on: boolean) => {
    saveSchoolMode(on);
    set({ schoolMode: on });
  },
  loadUserInfo: async () => {
    const { userInfo } = get();
    if (userInfo) return;
    try {
      const info = await apiGet<UserInfo>('/rost_max/api/user/info');
      set({ userInfo: info });
      // Валидация сохранённого ребёнка: id обязан быть в списке детей
      // ЭТОГО юзера (после логина другого юзера id протухает).
      // Дефолты: учитель — «Мои уроки» (null); чистый родитель — первый
      // ребёнок (строки «Мои уроки» у него нет).
      const children = info.children ?? [];
      const saved = get().selectedChildId;
      if (saved != null && !children.some(c => c.id === saved)) {
        set({ selectedChildId: null });
        saveChildId(null);
      }
      if (children.length > 0 && !info.is_teacher && !info.is_admin
          && get().selectedChildId == null) {
        const first = children[0].id;
        set({ selectedChildId: first });
        saveChildId(first);
      }
    } catch (e) {
      console.error('[store] loadUserInfo failed', e);
      set({ userInfo: null });
    }
  },
}));

export { useAppStore };
