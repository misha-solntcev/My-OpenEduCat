import React from 'react';

interface ToastProps {
  message: string;
  type?: 'info' | 'success' | 'error' | 'warning';
  duration?: number;
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ message, type = 'info', duration = 4000, onClose }) => {
  React.useEffect(() => {
    const timer = window.setTimeout(onClose, duration);
    return () => window.clearTimeout(timer);
  }, [duration, onClose]);

  const bgColor = {
    info: 'var(--background-surface-card)',
    success: 'var(--background-accent-positive)',
    error: 'var(--background-accent-negative)',
    warning: 'var(--background-accent-attention-primary)',
  }[type];

  const textColor = {
    info: 'var(--text-primary)',
    success: 'var(--text-primary-static)',
    error: 'var(--text-primary-static)',
    warning: 'var(--text-primary-static)',
  }[type];

  return (
    <div
      style={{
        backgroundColor: bgColor,
        color: textColor,
        padding: '12px 16px',
        borderRadius: '12px',
        marginBottom: '8px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
        animation: 'toast-in 0.3s ease-out',
        minWidth: '280px',
        maxWidth: '90vw',
      }}
    >
      {message}
    </div>
  );
};

interface ToastContainerState {
  toasts: Array<{ id: number; message: string; type: ToastProps['type'] }>;
  addToast: (message: string, type?: ToastProps['type'], duration?: number) => void;
  removeToast: (id: number) => void;
}

const createToastStore = () => {
  let state: ToastContainerState = {
    toasts: [],
    addToast: () => {},
    removeToast: () => {},
  };

  const listeners = new Set<() => void>();

  const notify = () => listeners.forEach(l => l());

  state.addToast = (message, type = 'info', duration = 4000) => {
    const id = Date.now();
    state.toasts = [...state.toasts, { id, message, type }];
    notify();
    if (duration > 0) {
      window.setTimeout(() => {
        state.removeToast(id);
      }, duration);
    }
  };

  state.removeToast = (id) => {
    state.toasts = state.toasts.filter(t => t.id !== id);
    notify();
  };

  return {
    getState: () => state,
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
};

const toastStore = createToastStore();

/** Хук для использования toast в любом месте приложения */
export const useToast = () => {
  const [, forceUpdate] = React.useReducer(x => x + 1, 0);
  React.useEffect(() => {
    toastStore.subscribe(() => {
      forceUpdate();
    });
  }, []);
  return toastStore.getState().addToast;
};

/** Глобальный контейнер для отображения всех toast-уведомлений */
export const ToastContainer: React.FC = () => {
  const [, forceUpdate] = React.useReducer(x => x + 1, 0);
  React.useEffect(() => {
    toastStore.subscribe(() => forceUpdate());
  }, []);

  // Инжектируем CSS анимацию один раз при монтировании
  React.useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes toast-in {
        from { opacity: 0; transform: translateY(20px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }
    `;
    document.head.appendChild(style);
    return () => {
      void document.head.removeChild(style);
    };
  }, []);

  const { toasts, removeToast } = toastStore.getState();

  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '90px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        pointerEvents: 'none',
        padding: '0 16px',
      }}
    >
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );
};