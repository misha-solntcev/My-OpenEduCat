import React from 'react';
import { Snackbar, Text } from '@vkontakte/vkui';

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

  const appearance = {
    info: 'neutral',
    success: 'positive',
    error: 'negative',
    warning: 'accent',
  }[type];

  return (
    <Snackbar
      open={true}
      onClose={onClose}
      onClosed={onClose}
      placement="bottom"
      duration={duration}
      appearance={appearance}
    >
      <Text weight="1" color="primary">{message}</Text>
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
    <>
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </>
  );
};