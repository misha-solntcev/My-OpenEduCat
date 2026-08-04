import React from 'react';
import { Box, Flex, Panel, Button } from '@vkontakte/vkui';
import { BulkSheet } from '@/pages/lesson-journal/components/BulkSheet';
import { LessonJournalContent } from '@/pages/lesson-journal/components/LessonJournalContent';
import { LessonJournalToolbar } from '@/pages/lesson-journal/components/LessonJournalToolbar';
import { useLessonJournal } from '@/pages/lesson-journal/hooks/useLessonJournal';
import { useBulkSheet } from '@/pages/lesson-journal/hooks/useBulkSheet';
import type { GradeField } from '@/shared/lib/types';

interface LessonJournalPageProps {
  id: string;
  lessonId: number | null;
  onBack: () => void;
}

export const LessonJournalPage: React.FC<LessonJournalPageProps> = ({ id, lessonId, onBack }) => {
  // Основная бизнес-логика вынесена в хук
  const {
    lesson,
    students,
    attendanceTypes,
    loading,
    error,
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
    loadStudents,
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

  // Если lessonId не передан (null) — показываем пустое состояние
  if (lessonId === null) {
    return <Panel id={id} />;
  }

  return (
    <Panel id={id}>
      <Flex direction="column" align="stretch" height="100dvh" width="100%">
        <LessonJournalToolbar
          lesson={lesson}
          showExitBanner={showExitBanner}
          setShowExitBanner={setShowExitBanner}
          onOpenBulkSheet={onOpenBulkSheet}
          exitSave={exitSave}
          exitDiscard={exitDiscard}
          handleBack={handleBack}
        />

        <Box
          flexGrow={1}
          overflowBlock="auto"
          padding="xl"
          paddingBlockEnd={dirty ? 84 : 24}
        >
          <LessonJournalContent
            loading={loading}
            error={error}
            onRetry={loadStudents}
            students={students}
            attendanceTypes={attendanceTypes}
            onCycleGrade={cycleGradeField}
            onCycleAttendance={cycleAttendance}
          />
        </Box>

        {dirty && (
          <Box position="sticky" insetBlockEnd={0} zIndex="popout" padding="m" paddingInline="l" border="top" background="content">
            <Button
              stretched
              size="l"
              mode="primary"
              appearance="accent"
              loading={saving}
              onClick={saveAll}
            >
              Сохранить
            </Button>
          </Box>
        )}
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
      </Flex>
    </Panel>
  );
};