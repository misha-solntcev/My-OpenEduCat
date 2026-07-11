import { create } from 'zustand';
import { apiGet } from '../shared/lib';
import { getSavedFilters, saveFilters, type TimetableFilters } from '../shared/lib';
import type { UserInfo } from '../entities/user';

interface AppState {
  // Профиль и роли
  userInfo: UserInfo | null;
  userLoading: boolean;
  loadUserInfo: () => Promise<void>;

  // Единая дата (Date Jumper): синхронизирует дашборд и расписание,
  // переживает reload через sessionStorage.
  globalDate: string;
  setGlobalDate: (date: string) => void;

  // Фильтры расписания (дата + преподаватель) — единая точка правды.
  filters: TimetableFilters;
  setFilters: (patch: Partial<TimetableFilters>) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  userInfo: null,
  userLoading: true,
  loadUserInfo: async () => {
    try {
      const info = await apiGet<UserInfo>('/rost_max/api/user/info');
      set({ userInfo: info, userLoading: false });
    } catch {
      // 401/403 -> api.ts уже редиректит на логин; здесь просто гасим
      set({ userInfo: null, userLoading: false });
    }
  },

  globalDate: getSavedFilters().date,
  setGlobalDate: (date: string) => {
    set({ globalDate: date });
    saveFilters({ date });
  },

  filters: getSavedFilters(),
  setFilters: (patch: Partial<TimetableFilters>) => {
    const next = { ...get().filters, ...patch };
    set({ filters: next });
    saveFilters(patch);
  },
}));
