import { create } from 'zustand';
import { apiGet } from './api';
import type { UserInfo } from './types';

interface AppState {
  // Профиль и роли
  userInfo: UserInfo | null;
  loadUserInfo: () => Promise<void>;

  // Флаг успешного логина — триггерит переход login -> main
  authSuccess: boolean;
  setAuthSuccess: (v: boolean) => void;
}

// Хранилище (создаём сначала)
const useAppStore = create<AppState>((set, get) => ({
  userInfo: null,
  authSuccess: false,
  setAuthSuccess: (v: boolean) => set({ authSuccess: v }),
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
