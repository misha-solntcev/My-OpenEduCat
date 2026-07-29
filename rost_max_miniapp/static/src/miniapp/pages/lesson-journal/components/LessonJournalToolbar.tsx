import React from 'react';
import { SaveBar } from './SaveBar';
import { ExitBanner } from '@/shared/components/ExitBanner';
import { LessonHeader } from './LessonHeader';

interface LessonJournalToolbarProps {
  lesson: { subject: string; batch: string; date: string; timing: string } | null;
  saving: boolean;
  dirty: boolean;
  showExitBanner: boolean;
  setShowExitBanner: (v: boolean) => void;
  onOpenBulkSheet: () => void;
  onSave: () => Promise<void>;
  exitSave: () => Promise<void>;
  exitDiscard: () => void;
  handleBack: () => void;
}

/** Тулбар журнала: хедер + SaveBar + ExitBanner */
export const LessonJournalToolbar: React.FC<LessonJournalToolbarProps> = ({
  lesson,
  saving,
  dirty,
  showExitBanner,
  setShowExitBanner,
  onOpenBulkSheet,
  onSave,
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
      <SaveBar saving={saving} dirty={dirty} onSave={onSave} />
      <ExitBanner
        visible={showExitBanner}
        onClose={() => setShowExitBanner(false)}
        onSave={exitSave}
        onDiscard={exitDiscard}
        saving={saving}
      />
    </>
  );
};