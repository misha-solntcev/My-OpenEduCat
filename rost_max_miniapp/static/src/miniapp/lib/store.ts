import { create } from 'zustand';
import { apiGet } from './api';
import { getSavedFilters, saveFilters, type TimetableFilters } from './storage';
import type { UserInfo } from './types';

interface AppState {
  // Профиль и роли
  userInfo: UserInfo | null;
  userLoading: boolean;
  loadUserInfo: () => Promise<void>;

  // Единая дата (Date Jumper): синхронизирует дашборд и расписание,
  // переживает reload внутри сессии через sessionStorage. Источник правды —
  // filters.date (см. ниже); globalDate здесь НЕ дублируется.
  getGlobalDate: () => string;
  setGlobalDate: (date: string) => void;

  // Фильтры расписания (дата + преподаватель) — единая точка правды.
  // globalDate вынесен (дубль устранён): дата = filters.date.
  filters: TimetableFilters;
  setFilters: (patch: Partial<TimetableFilters>) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  userInfo: null,
  userLoading: true,
  loadUserInfo: async () => {
    const { userInfo } = get();
    // Если профиль уже загружен — не дублируем запрос (защита от повторных
    // вызовов при переключении вкладок / ре-рендерах).
    if (userInfo) return;
    set({ userLoading: true });
    try {
      const info = await apiGet<UserInfo>('/rost_max/api/user/info');
      set({ userInfo: info, userLoading: false });
    } catch (e) {
      // 401 -> api.ts редиректит на логин. 403 (нет прав на данные) НЕ
      // редиректит (иначе student с валидной сессии вылетал бы на логин).
      // Здесь просто гасим и логируем для дебага сетевых/неожиданных падений.
      console.error('[store] loadUserInfo failed', e);
      set({ userInfo: null, userLoading: false });
    }
  },

  // Дата — производная от filters.date (single source of truth).
  getGlobalDate: () => get().filters.date,
  setGlobalDate: (date: string) => get().setFilters({ date }),

  // При старте: читаем сохранённые фильтры; если sessionStorage пуст
  // (новая сессия / закрытая вкладка), getSavedFilters() вернёт today.
  // Внутри живой сессии (F5, переключение табов) сохранённая дата
  // восстанавливается. Явный сброс на today при входе делает
  // handleLoginSuccess (см. app/App.tsx).
  filters: getSavedFilters(),
  setFilters: (patch: Partial<TimetableFilters>) => {
    const next = { ...get().filters, ...patch };
    set({ filters: next });
    saveFilters(patch);
  },
}));
