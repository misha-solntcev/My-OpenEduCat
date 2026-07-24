import React from 'react';
import { Flex, Title, Text, IconButton } from '@vkontakte/vkui';
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
    <div className="rm-lesson-header">
      <Flex align="center" gap={12} style={{ width: '100%' }}>
        <IconButton label="Назад" onClick={onBack}>
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </IconButton>
        <div className="rm-lesson-header-title">
          <Title level="3" weight="2">
            {headerTitle}
          </Title>
        </div>
        <IconButton
          label="Массово проставить оценки и посещаемость"
          onClick={onOpenBulkSheet}
          style={{ flexShrink: 0 }}
        >
          <Zap size={20} color="currentColor" />
        </IconButton>
      </Flex>
      {headerSubtitle && (
        <Text weight="2" className="rm-lesson-header-subtitle">
          {headerSubtitle}
        </Text>
      )}
    </div>
  );
};