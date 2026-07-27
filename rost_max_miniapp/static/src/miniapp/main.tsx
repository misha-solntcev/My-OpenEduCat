import { createRoot } from 'react-dom/client';
import { ConfigProvider, AdaptivityProvider } from '@vkontakte/vkui';
import '@vkontakte/vkui/dist/vkui.css';
import App from './App';

// MAX Bridge: типы для WebView API
declare global {
  interface Window {
    WebApp?: {
      expand: () => void;
      ready: () => void;
      platform: string;
      theme: string;
    };
  }
}

window.WebApp?.expand();
window.WebApp?.ready();

const Root = () => (
  <ConfigProvider>
    <AdaptivityProvider>
      <App />
    </AdaptivityProvider>
  </ConfigProvider>
);

createRoot(document.getElementById('root')!).render(<Root />);