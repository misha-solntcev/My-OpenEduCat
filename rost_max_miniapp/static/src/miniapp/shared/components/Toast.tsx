import React from 'react';
import { Snackbar, Box } from '@vkontakte/vkui';

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

  const backgroundColor = {
    info: 'var(--vkui--color_background_surface_card)',
    success: 'var(--vkui--color_background_accent_positive)',
    error: 'var(--vkui--color_background_accent_negative)',
    warning: 'var(--vkui--color_background_accent_attention_primary)',
  }[type];

  const color = {
    info: 'var(--vkui--color_text_primary)',
    success: 'var(--vkui--color_text_primary_static)',
    error: 'var(--vkui--color_text_primary_static)',
    warning: 'var(--vkui--color_text_primary_static)',
  }[type];

  return (
    <Snackbar
      open={true}
      onClose={onClose}
      placement="bottom"
      duration={duration}
      style={{ backgroundColor, color, borderRadius: '12px', padding: '12px 16px', minWidth: '280px', maxWidth: '90vw' } as React.CSSProperties}
    >
      {message}
    </Snackbar>
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
      return () => { listeners.delete(listener); };
    },
  };
};

const toastStore = createToastStore();

export const useToast = () => {
  const [, forceUpdate] = React.useReducer(x => x + 1, 0);
  React.useEffect(() => {
    toastStore.subscribe(() => { forceUpdate(); });
  }, []);
  return toastStore.getState().addToast;
};

export const ToastContainer: React.FC = () => {
  const [, forceUpdate] = React.useReducer(x => x + 1, 0);
  React.useEffect(() => {
    toastStore.subscribe(() => forceUpdate());
  }, []);

  const { toasts, removeToast } = toastStore.getState();

  if (toasts.length === 0) return null;

  return (
    <Box style={{ position: 'fixed', bottom: '90px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, display: 'flex', flexDirection: 'column', alignItems: 'center', pointerEvents: 'none', padding: '0 16px' }}>
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </Box>
  );
};