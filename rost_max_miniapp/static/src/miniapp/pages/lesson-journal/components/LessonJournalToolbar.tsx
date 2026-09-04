import React from 'react';
import { ExitBanner } from '@/shared/components/ExitBanner';
import { LessonHeader } from './LessonHeader';

interface LessonJournalToolbarProps {
  lesson: { subject: string; batch: string; date: string; timing: string } | null;
  showExitBanner: boolean;
  setShowExitBanner: (v: boolean) => void;
  onOpenBulkSheet?: () => void;
  onOpenColumnsSettings?: () => void;
  exitSave: () => Promise<void>;
  exitDiscard: () => void;
  handleBack: () => void;
  saving: boolean;
}

/** Тулбар журнала: хедер + SaveBar + ExitBanner */
export const LessonJournalToolbar: React.FC<LessonJournalToolbarProps> = ({
  lesson,
  showExitBanner,
  setShowExitBanner,
  onOpenBulkSheet,
  onOpenColumnsSettings,
  exitSave,
  exitDiscard,
  handleBack,
  saving: savingProp,
}) => {
  const header = (
    <LessonHeader
      lesson={lesson}
      onBack={handleBack}
      onOpenBulkSheet={onOpenBulkSheet}
      onOpenColumnsSettings={onOpenColumnsSettings}
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
        saving={savingProp}
      />
    </>
  );
};
