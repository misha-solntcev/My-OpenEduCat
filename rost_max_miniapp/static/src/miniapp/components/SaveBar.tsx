import React from 'react';
import { Button } from '@maxhub/max-ui';

interface SaveBarProps {
  saving: boolean;
  dirty: boolean;
  onSave: () => Promise<void>;
}

/**
 * Нижняя фиксированная панель «Сохранить» — показывается только когда есть несохранённые правки.
 */
export const SaveBar: React.FC<SaveBarProps> = ({ saving, dirty, onSave }) => {
  if (!dirty) return null;

  return (
    <div className="rm-save-bar">
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
};