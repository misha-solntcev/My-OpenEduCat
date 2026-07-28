import { createRoot } from 'react-dom/client';
import { ConfigProvider, AdaptivityProvider, AppRoot } from '@vkontakte/vkui';
import '@vkontakte/vkui/dist/vkui.css';
import App from './App';

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
  // Настройка темы и платформы на самом верхнем уровне приложения один раз
  const maxTheme = window.WebApp?.theme === 'dark' ? 'dark' : 'light';
  const maxPlatform = window.WebApp?.platform === 'ios' ? 'ios' : 'android';

  return (
    <ConfigProvider colorScheme={maxTheme} platform={maxPlatform} isWebView={true}>
      <AdaptivityProvider>
        <AppRoot mode="full">
          <App />
        </AppRoot>
      </AdaptivityProvider>
    </ConfigProvider>
  );
};

createRoot(document.getElementById('root')!).render(<Root />);