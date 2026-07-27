import React from 'react';
import { PanelHeader, Title, Text, IconButton } from '@vkontakte/vkui';
import { Zap } from 'lucide-react';

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
      before={<IconButton label="Назад" onClick={onBack}><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6" /></svg></IconButton>}
      after={<IconButton label="Массово проставить оценки и посещаемость" onClick={onOpenBulkSheet}><Zap size={20} color="currentColor" /></IconButton>}
    >
      <Title level="3" weight="2">{headerTitle}</Title>
      {headerSubtitle && <Text weight="2" inline>{headerSubtitle}</Text>}
    </PanelHeader>
  );
};