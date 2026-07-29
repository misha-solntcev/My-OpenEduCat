import React from 'react';
import { Box, Button } from '@vkontakte/vkui';

interface SaveBarProps {
  saving: boolean;
  dirty: boolean;
  onSave: () => Promise<void>;
}

export const SaveBar: React.FC<SaveBarProps> = ({ saving, dirty, onSave }) => {
  if (!dirty) return null;

  return (
    <Box
      position="fixed"
      insetInlineStart={0}
      insetInlineEnd={0}
      insetBlockEnd={0}
      padding="m"
      style={{
        backgroundColor: 'var(--background-surface-card)',
        borderTop: '1px solid var(--stroke-separator-secondary)',
        zIndex: 90,
      }}
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
    </Box>
  );
};