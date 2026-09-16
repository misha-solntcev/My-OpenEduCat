import React from 'react';

import { createRoot } from 'react-dom/client';
import {
  ConfigProvider,
  AdaptivityProvider,
  AppRoot,
  ColorSchemeProvider,
} from '@vkontakte/vkui';
import '@vkontakte/vkui/dist/vkui.css';
import App from './App';
import { ErrorBoundary } from './shared/components/ErrorBoundary';
import { useAppStore } from '@/shared/lib/store';
import { resolveColorScheme, usePrefersDark } from '@/shared/lib/theme';

// MAX Bridge: типы для WebView API
declare global {
  interface Window {
    WebApp?: {      
      platform: string;
      theme: 'light' | 'dark';
      initData?: string;
      initDataUnsafe?: {
        query_id: string;
        auth_date: number;
        hash: string;
        user?: {
          id: number;
          first_name: string;
          last_name: string;
          username: string;
          language_code: string;
          photo_url: string;
        };
        chat?: {
          id: number;
          type: 'DIALOG' | 'CHAT' | 'CHANNEL';
        };
        start_param?: string;
      };
    };
  }
}

const Root = () => {
  // Настройка платформы на самом верхнем уровне приложения один раз.
  // colorScheme НЕ передаём — MAX Bridge не даёт тему.
  // VKUI сам подхватит системную тему через CSS prefers-color-scheme + meta color-scheme.
  const maxPlatform = window.WebApp?.platform === 'ios' ? 'ios' : 'android';

  // Выбор юзера в профиле: light / dark / system.
  // Схему резолвим ВСЕГДА в конкретное значение (system — через matchMedia,
  // как useAutoDetectColorScheme внутри VKUI), ColorSchemeProvider рендерим
  // безусловно: если убрать его для «системной», меняется форма дерева,
  // React перемонтирует приложение и сбрасывает навигацию (выбрасывало
  // на главный экран при переключении тёмная ↔ системная).
  const themePreference = useAppStore(s => s.themePreference);
  const prefersDark = usePrefersDark();
  const colorScheme = resolveColorScheme(themePreference, prefersDark);

  return (
    <ConfigProvider platform={maxPlatform} isWebView={true}>
      <ColorSchemeProvider value={colorScheme}>
        <ThemeAppRoot />
      </ColorSchemeProvider>
    </ConfigProvider>
  );
};

// AppRoot + дерево приложения. Вынесен, чтобы ColorSchemeProvider оборачивал
// только содержимое (AppRoot внутри получит переопределённую схему из контекста).
const ThemeAppRoot: React.FC = () => (
  <AdaptivityProvider>
    {/* layout="card": фон страницы = background (серый/тёмный), карточки
        = content (белый/#19191a) — как в настройках MAX. Без layout Panel
        в WebView получает mode=none и красит всю страницу в content,
        из-за чего карточки на том же токене сливаются с фоном. */}
    <AppRoot mode="full" layout="card" safeAreaInsets={{ top: 0 }} style={{ background: 'var(--vkui--color_background)' }}>
      {/* В MAX WebView нет консоли: без Boundary render-error = белый экран */}
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </AppRoot>
  </AdaptivityProvider>
);

createRoot(document.getElementById('root')!).render(<Root />);
