import React from 'react';
import { Caption } from '@vkontakte/vkui';
import { ExitBanner } from '@/shared/components/ExitBanner';
import { LessonHeader } from './LessonHeader';

interface LessonJournalToolbarProps {
  lesson: {
    subject: string; batch: string; date: string; timing: string;
    /** Четверть урока (api_lesson_students). Нет значения — строку не рисуем. */
    quarter?: number | null;
  } | null;
  showExitBanner: boolean;
  setShowExitBanner: (v: boolean) => void;
  onOpenBulkSheet?: () => void;
  onOpenColumnsSettings?: () => void;
  exitSave: () => Promise<void>;
  exitDiscard: () => void;
  handleBack: () => void;
  saving: boolean;
}

/** Тулбар журнала: хедер + строка контекста урока + SaveBar + ExitBanner.
 *  Строка контекста («09:30 - 10:10 · 2 четверть») — статичный индикатор, НЕ
 *  фильтр: в журнале один урок одного класса, фильтровать нечего. Класс
 *  остался подзаголовком в шапке, предмет — её заголовком, поэтому здесь
 *  только то, чего в шапке не было: время и четверть. */
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

  const contextLine = lesson
    ? [
        lesson.timing,
        lesson.quarter != null ? `${lesson.quarter} четверть` : '',
      ].filter(Boolean).join(' · ')
    : '';

  return (
    <>
      {header}
      {contextLine && (
        <Caption
          level="1"
          style={{
            display: 'block',
            padding: '0 16px 6px',
            color: 'var(--vkui--color_text_secondary)',
          }}
        >
          {contextLine}
        </Caption>
      )}
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
