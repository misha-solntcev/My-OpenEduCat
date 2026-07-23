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
    <div className="rm-exit-banner-overlay" onClick={onClose}>
      <div
        onClick={e => e.stopPropagation()}
        className="rm-exit-banner-card"
      >
        <div className="rm-exit-banner-title">
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