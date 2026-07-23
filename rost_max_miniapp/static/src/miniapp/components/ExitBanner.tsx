import React from 'react';
import { Flex, Button } from '@maxhub/max-ui';

interface ExitBannerProps {
  visible: boolean;
  onClose: () => void;
  onSave: () => Promise<void>;
  onDiscard: () => void;
  saving: boolean;
}

/**
 * Банер подтверждения выхода с несохранёнными изменениями.
 * Появляется поверх всего контента (fixed overlay).
 */
export const ExitBanner: React.FC<ExitBannerProps> = ({
  visible,
  onClose,
  onSave,
  onDiscard,
  saving,
}) => {
  if (!visible) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.5)',
        zIndex: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '360px',
          backgroundColor: 'var(--background-surface-card)',
          borderRadius: '16px',
          padding: '20px 16px calc(16px + env(safe-area-inset-bottom))',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', color: 'var(--text-primary)' }}>
          Сохранить изменения?
        </div>
        <Flex direction="column" gap={10} style={{ width: '100%' }}>
          <Button
            stretched
            size="large"
            mode="primary"
            appearance="themed"
            loading={saving}
            onClick={onSave}
          >
            Да, сохранить
          </Button>
          <Button
            stretched
            size="large"
            mode="secondary"
            loading={saving}
            onClick={onDiscard}
          >
            Нет, не сохранять
          </Button>
          <Button
            stretched
            size="large"
            mode="tertiary"
            onClick={onClose}
          >
            Остаться
          </Button>
        </Flex>
      </div>
    </div>
  );
};