import React from 'react';
import { ExitBanner } from '@/shared/components/ExitBanner';
import { LessonHeader } from './LessonHeader';

interface LessonJournalToolbarProps {
  lesson: { subject: string; batch: string; date: string; timing: string } | null;
  showExitBanner: boolean;
  setShowExitBanner: (v: boolean) => void;
  onOpenBulkSheet?: () => void;
  exitSave: () => Promise<void>;
  exitDiscard: () => void;
  handleBack: () => void;
}

/** Тулбар журнала: хедер + SaveBar + ExitBanner */
export const LessonJournalToolbar: React.FC<LessonJournalToolbarProps> = ({
  lesson,
  showExitBanner,
  setShowExitBanner,
  onOpenBulkSheet,
  exitSave,
  exitDiscard,
  handleBack,
}) => {
  const header = (
    <LessonHeader
      lesson={lesson}
      onBack={handleBack}
      onOpenBulkSheet={onOpenBulkSheet}
    />
  );

  return (
    <>
      {header}
      <ExitBanner
        visible={showExitBanner}
        onClose={() => setShowExitBanner(false)}
        onSave={exitSave}
        onDiscard={exitDiscard}
      />
    </>
  );
};