import React from 'react';
import { Button } from '@maxhub/max-ui';

interface SaveBarProps {
  saving: boolean;
  onSave: () => Promise<void>;
}

/**
 * Нижняя фиксированная панель «Сохранить» — показывается только когда есть несохранённые правки.
 */
export const SaveBar: React.FC<SaveBarProps> = ({ saving, onSave }) => (
  <div
    style={{
      position: 'fixed',
      left: 0,
      right: 0,
      bottom: 0,
      padding: '12px 16px calc(12px + env(safe-area-inset-bottom))',
      backgroundColor: 'var(--background-surface-card)',
      borderTop: '1px solid var(--stroke-separator-secondary)',
      zIndex: 90,
    }}
  >
    <Button
      stretched
      size="large"
      mode="primary"
      appearance="themed"
      loading={saving}
      onClick={onSave}
    >
      Сохранить
    </Button>
  </div>
);