import { createRoot } from 'react-dom/client';
import { MaxUI } from '@maxhub/max-ui';
import '@maxhub/max-ui/dist/styles.css';
import './index.css';
import App from './app/App';

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
  <MaxUI>
    <App />
  </MaxUI>
);

createRoot(document.getElementById('root')!).render(<Root />);