import React from 'react';
import { Box, Flex } from '@vkontakte/vkui';
import { BulkSheet } from '@/components/BulkSheet';
import { LessonJournalContent } from '@/components/LessonJournalContent';
import { LessonJournalToolbar } from '@/components/LessonJournalToolbar';
import { useLessonJournal } from '@/hooks/useLessonJournal';
import { useBulkSheet } from '@/hooks/useBulkSheet';
import type { GradeField } from '@/lib/types';

interface LessonJournalPageProps {
  lessonId: number;
  onBack: () => void;
}

export const LessonJournalPage: React.FC<LessonJournalPageProps> = ({ lessonId, onBack }) => {
  // Основная бизнес-логика вынесена в хук
  const {
    lesson,
    students,
    attendanceTypes,
    loading,
    dirty,
    saving,
    showExitBanner,
    setShowExitBanner,
    cycleGradeField,
    cycleAttendance,
    saveAll,
    handleBack,
    exitSave,
    exitDiscard,
    // Массовые операции для BulkSheet
    bulkSetGrade: bulkSetGradeLocal,
    bulkSetAtt: bulkSetAttLocal,
    clearAll: clearAllLocal,
  } = useLessonJournal(lessonId, onBack);

  // Логика массовой шторки вынесена в отдельный хук
  const bulkSetGrade = (field: GradeField, value: number | null) => {
    bulkSetGradeLocal(field, value, overwriteFilled, baselineRef);
  };
  const bulkSetAtt = (attId: number | null) => {
    bulkSetAttLocal(attId, overwriteFilled, baselineRef);
  };
  const clearAll = () => {
    clearAllLocal();
  };

  const {
    overwriteFilled,
    setOverwriteFilled,
    baselineRef,
    resetBaseline,
  } = useBulkSheet(
    students,
    attendanceTypes,
    false,
    bulkSetGrade,
    bulkSetAtt,
    clearAll
  );

  const [sheetOpen, setSheetOpen] = React.useState(false);

  const onOpenBulkSheet = () => {
    resetBaseline(students);
    setSheetOpen(true);
  };

  return (
    <Flex direction="column" align="stretch" style={{ width: '100%', height: '100dvh' }}>
      <LessonJournalToolbar
        lesson={lesson}
        saving={saving}
        dirty={dirty}
        showExitBanner={showExitBanner}
        setShowExitBanner={setShowExitBanner}
        onOpenBulkSheet={onOpenBulkSheet}
        onSave={saveAll}
        exitSave={exitSave}
        exitDiscard={exitDiscard}
        handleBack={handleBack}
      />

      <Box
        flexGrow={1}
        overflowBlock="auto"
        padding="xl"
        paddingBlockEnd={dirty ? '84px' : '24px'}
        style={{ WebkitOverflowScrolling: 'touch' }}
      >
        <LessonJournalContent
          loading={loading}
          students={students}
          attendanceTypes={attendanceTypes}
          onCycleGrade={cycleGradeField}
          onCycleAttendance={cycleAttendance}
        />
      </Box>

      {sheetOpen && (
        <BulkSheet
          attendanceTypes={attendanceTypes}
          overwriteFilled={overwriteFilled}
          onOverwriteFilledChange={setOverwriteFilled}
          onBulkGrade={bulkSetGrade}
          onBulkAtt={bulkSetAtt}
          onClearAll={clearAll}
          onClose={() => setSheetOpen(false)}
          open={sheetOpen}
        />
      )}
    </Flex>
  );
};