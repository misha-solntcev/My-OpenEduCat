import React from 'react';
import { PanelHeader, Title, Text, IconButton } from '@vkontakte/vkui';
import { Icon28ChevronBack, Icon28FlashOutline, Icon28SettingsOutline } from '@vkontakte/icons';

interface LessonHeaderProps {
  lesson: { subject?: string; batch?: string; timing?: string } | null;
  onBack: () => void;
  onOpenBulkSheet?: () => void;
  onOpenColumnsSettings?: () => void;
}

/** Хедер журнала: назад слева; справа — сперва молния (массовая), потом шестерёнка (настройки). */
export const LessonHeader: React.FC<LessonHeaderProps> = ({
  lesson,
  onBack,
  onOpenBulkSheet,
  onOpenColumnsSettings,
}) => {
  const headerTitle = lesson ? (lesson.subject || 'Журнал оценок') : 'Журнал оценок';
  const headerSubtitle = lesson
    ? [lesson.batch, lesson.timing].filter(Boolean).join(' · ')
    : '';

  return (
    <PanelHeader
      before={
        <IconButton label="Назад" onClick={onBack}>
          <Icon28ChevronBack />
        </IconButton>
      }
      after={
        <>
          {onOpenBulkSheet && (
            <IconButton
              label="Массово проставить оценки и посещаемость"
              onClick={onOpenBulkSheet}
            >
              <Icon28FlashOutline />
            </IconButton>
          )}
          {onOpenColumnsSettings && (
            <IconButton label="Настройки журнала" onClick={onOpenColumnsSettings}>
              <Icon28SettingsOutline />
            </IconButton>
          )}
        </>
      }
    >
      <Title level="3" weight="2">{headerTitle}</Title>
      {headerSubtitle && <Text weight="2" inline>{headerSubtitle}</Text>}
    </PanelHeader>
  );
};
