import React from 'react';
import { Panel, Button } from '@vkontakte/vkui';

interface SaveBarProps {
  saving: boolean;
  dirty: boolean;
  onSave: () => Promise<void>;
}

export const SaveBar: React.FC<SaveBarProps> = ({ saving, dirty, onSave }) => {
  if (!dirty) return null;

  return (
    <Panel
      position="fixed"
      insetInlineStart={0}
      insetInlineEnd={0}
      insetBlockEnd={0}
      mode="card"
      padding="m"
      border="top"
      style={{ zIndex: 90 }}
    >
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
    </Panel>
  );
};