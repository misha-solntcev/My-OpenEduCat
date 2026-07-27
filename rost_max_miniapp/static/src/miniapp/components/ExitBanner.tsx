import React from 'react';
import { ModalCard, Button, ButtonGroup } from '@vkontakte/vkui';

interface ExitBannerProps {
  visible: boolean;
  onClose: () => void;
  onSave: () => Promise<void>;
  onDiscard: () => void;
  saving: boolean;
}

/**
 * Банер подтверждения выхода с несохранёнными изменениями.
 * Использует VKUI ModalCard вместо кастомных CSS-классов.
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
    <ModalCard
      open={visible}
      onClose={onClose}
      title="Сохранить изменения?"
      size={360}
      actions={
        <ButtonGroup gap="m" mode="vertical" stretched>
          <Button
            size="l"
            mode="primary"
            appearance="accent"
            loading={saving}
            onClick={onSave}
          >
            Да, сохранить
          </Button>
          <Button
            size="l"
            mode="secondary"
            loading={saving}
            onClick={onDiscard}
          >
            Нет, не сохранять
          </Button>
          <Button
            size="l"
            mode="tertiary"
            onClick={onClose}
          >
            Остаться
          </Button>
        </ButtonGroup>
      }
    />
  );
};