import React from 'react';
import { Flex, Typography, IconButton } from '@maxhub/max-ui';
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
        <IconButton appearance="themed" mode="tertiary" onClick={onBack}>
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
          <Typography.Title variant="small-strong">
            {headerTitle}
          </Typography.Title>
        </div>
        <IconButton
          appearance="themed"
          mode="tertiary"
          onClick={onOpenBulkSheet}
          title="Массово проставить оценки и посещаемость"
          style={{ flexShrink: 0 }}
        >
          <Zap size={20} color="currentColor" />
        </IconButton>
      </Flex>
      {headerSubtitle && (
        <Typography.Label variant="small-strong" className="rm-lesson-header-subtitle">
          {headerSubtitle}
        </Typography.Label>
      )}
    </div>
  );
};