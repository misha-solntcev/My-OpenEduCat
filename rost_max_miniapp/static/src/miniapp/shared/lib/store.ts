import { create } from 'zustand';
import { apiGet, hasSavedSession } from './api';
import type { UserInfo } from './types';

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
  loadUserInfo: async () => {
    const { userInfo } = get();
    if (userInfo) return;
    try {
      const info = await apiGet<UserInfo>('/rost_max/api/user/info');
      set({ userInfo: info });
    } catch (e) {
      console.error('[store] loadUserInfo failed', e);
      set({ userInfo: null });
    }
  },
}));

export { useAppStore };
