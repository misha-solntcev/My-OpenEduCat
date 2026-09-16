// Пользовательская тема: светлая / тёмная / системная.
// VKUI v8: схема переключается классом токенов на <html>, который AppRoot
// ставит по значению colorScheme. Если colorScheme в ConfigProvider не задан —
// VKUI сам слушает matchMedia('(prefers-color-scheme: dark)') (системная).
// Поэтому «системная» = не мешать, а «светлая/тёмная» = ColorSchemeProvider
// с явным значением (он внутри делает ConfigProviderOverride + media query
// отключается, см. hooks/useAutoDetectColorScheme.js в vkui dist).

import React from 'react';
import type { ColorSchemeType } from '@vkontakte/vkui';

export type ThemePreference = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'rost_max_theme';

export function loadThemePreference(): ThemePreference {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'light' || raw === 'dark' || raw === 'system') return raw;
  } catch {
    // localStorage недоступен (приватный режим) — работает системная тема
  }
  return 'system';
}

export function saveThemePreference(pref: ThemePreference): void {
  try {
    localStorage.setItem(STORAGE_KEY, pref);
  } catch {
    // недоступно — тема просто не переживёт перезапуск WebView
  }
}

// Слушаем системную тему сами (так же делает useAutoDetectColorScheme внутри
// VKUI). Нельзя оставлять colorScheme=undefined / убирать ColorSchemeProvider
// для «системной»: тернарник меняет форму дерева, React перемонтирует
// приложение и сбрасывает навигацию (выбрасывало на главный экран).
export function usePrefersDark(): boolean {
  const subscribe = React.useCallback((onChange: () => void) => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);
  const getSnapshot = React.useCallback(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches,
    []
  );
  return React.useSyncExternalStore(subscribe, getSnapshot, () => false);
}

// Всегда конкретная схема: 'system' → по matchMedia, иначе выбор юзера.
export function resolveColorScheme(pref: ThemePreference, prefersDark: boolean): ColorSchemeType {
  if (pref === 'system') return prefersDark ? 'dark' : 'light';
  return pref;
}
