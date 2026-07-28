import { create } from 'zustand';
import { apiGet } from './api';
import { getSavedFilters, saveFilters, type TimetableFilters } from './storage';
import type { UserInfo } from './types';

interface AppState {
  // Профиль и роли
  userInfo: UserInfo | null;
  userLoading: boolean;
  loadUserInfo: () => Promise<void>;

  // Флаг успешного логина — триггерит переход login -> main
  authSuccess: boolean;
  setAuthSuccess: (v: boolean) => void;

  // Фильтры расписания (дата + преподаватель) — единая точка правды.
  filters: TimetableFilters;
  setFilters: (patch: Partial<TimetableFilters>) => void;
}

// Хранилище (создаём сначала)
const useAppStore = create<AppState>((set, get) => ({
  userInfo: null,
  userLoading: true,
  authSuccess: false,
  setAuthSuccess: (v: boolean) => set({ authSuccess: v }),
  loadUserInfo: async () => {
    const { userInfo } = get();
    if (userInfo) return;
    set({ userLoading: true });
    try {
      const info = await apiGet<UserInfo>('/rost_max/api/user/info');
      set({ userInfo: info, userLoading: false });
    } catch (e) {
      console.error('[store] loadUserInfo failed', e);
      set({ userInfo: null, userLoading: false });
    }
  },

  filters: getSavedFilters(),
  setFilters: (patch: Partial<TimetableFilters>) => {
    const next = { ...get().filters, ...patch };
    set({ filters: next });
    saveFilters(patch);
  },
}));

// Селекторы (вынесены после создания store)
export const selectGlobalDate = (state: { filters: TimetableFilters }) => state.filters.date;

export const setGlobalDate = (date: string) => {
  useAppStore.getState().setFilters({ date });
};

export { useAppStore };