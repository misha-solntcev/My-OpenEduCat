import React from 'react';
import { PanelHeader, Title, Text, IconButton } from '@vkontakte/vkui';
import { Icon28ChevronBack, Icon28FlashOutline } from '@vkontakte/icons';

interface LessonHeaderProps {
  lesson: { subject?: string; batch?: string; timing?: string } | null;
  onBack: () => void;
  onOpenBulkSheet: () => void;
}

export const LessonHeader: React.FC<LessonHeaderProps> = ({
  lesson,
  onBack,
  onOpenBulkSheet,
}) => {
  const headerTitle = lesson ? (lesson.subject || 'Журнал оценок') : 'Журнал оценок';
  const headerSubtitle = lesson
    ? [lesson.batch, lesson.timing].filter(Boolean).join(' · ')
    : '';

  return (
    <PanelHeader
      before={<IconButton label="Назад" onClick={onBack}><Icon28ChevronBack /></IconButton>}
      after={<IconButton label="Массово проставить оценки и посещаемость" onClick={onOpenBulkSheet}><Icon28FlashOutline /></IconButton>}
    >
      <Title level="3" weight="2">{headerTitle}</Title>
      {headerSubtitle && <Text weight="2" inline>{headerSubtitle}</Text>}
    </PanelHeader>
  );
};