import React from 'react';
import { Button } from '@vkontakte/vkui';

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
        size="l"
        mode="primary"
        appearance="accent"
        loading={saving}
        onClick={onSave}
      >
        Сохранить
      </Button>
    </div>
  );
};