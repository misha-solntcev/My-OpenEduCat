import React from 'react';
import { Box, Flex, Panel, Button } from '@vkontakte/vkui';
import { BulkSheet } from '@/pages/lesson-journal/components/BulkSheet';
import { ColumnsSettingsSheet } from '@/pages/lesson-journal/components/ColumnsSettingsSheet';
import { TopicHomeworkCard } from '@/pages/lesson-journal/components/TopicHomeworkCard';
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
    columns,
    loading,
    error,
    dirty,
    saving,
    showExitBanner,
    setShowExitBanner,
    cycleGradeField,
    cycleAttendance,
    setRemark,
    setTopic,
    setHomework,
    saveAll,
    toggleColumn,
    handleBack,
    exitSave,
    exitDiscard,
    loadStudents,
    // Массовые операции для BulkSheet
    bulkSetGrade: bulkSetGradeLocal,
    bulkSetAtt: bulkSetAttLocal,
    bulkSetRemark: bulkSetRemarkLocal,
    clearAll: clearAllLocal,
  } = useLessonJournal(lessonId, onBack);

  // Ученик/родитель: бэкенд отдал только его строки и can_edit=false
  const canEdit = lesson?.can_edit !== false;

  // Логика массовой шторки вынесена в отдельный хук
  const bulkSetGrade = (field: GradeField, value: number | null) => {
    bulkSetGradeLocal(field, value, overwriteFilled, baselineRef);
  };
  const bulkSetAtt = (attId: number | null) => {
    bulkSetAttLocal(attId, overwriteFilled, baselineRef);
  };
  const bulkSetRemark = (remark: string) => {
    bulkSetRemarkLocal(remark, overwriteFilled, baselineRef);
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
    canEdit ? bulkSetGrade : () => {},
    canEdit ? bulkSetAtt : () => {},
    canEdit ? clearAll : () => {}
  );

  const [sheetOpen, setSheetOpen] = React.useState(false);
  const [columnsOpen, setColumnsOpen] = React.useState(false);

  const onOpenBulkSheet = canEdit
    ? () => {
        resetBaseline(students);
        setSheetOpen(true);
      }
    : undefined;

  const onOpenColumnsSettings = canEdit
    ? () => setColumnsOpen(true)
    : undefined;

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
          onOpenColumnsSettings={onOpenColumnsSettings}
          exitSave={exitSave}
          exitDiscard={exitDiscard}
          handleBack={handleBack}
          saving={saving}
        />

        <Box
          flexGrow={1}
          overflowBlock="auto"
          padding="xl"
          paddingBlockEnd={canEdit && dirty ? 84 : 24}
        >
          {lesson && (
            <Box paddingBlockEnd="l">
              <TopicHomeworkCard
                lesson={lesson}
                canEdit={canEdit}
                onTopicChange={setTopic}
                onHomeworkChange={setHomework}
              />
            </Box>
          )}

          <LessonJournalContent
            loading={loading}
            error={error}
            onRetry={loadStudents}
            students={students}
            attendanceTypes={attendanceTypes}
            columns={columns}
            canEdit={canEdit}
            onCycleGrade={cycleGradeField}
            onCycleAttendance={cycleAttendance}
            onRemarkChange={setRemark}
          />
        </Box>

        {canEdit && dirty && (
          <Box position="sticky" insetBlockEnd={0} zIndex="popout" padding="m" paddingInline="l" style={{ borderTop: '1px solid var(--vkui--color_separator_primary)', backgroundColor: 'var(--vkui--color_background_content)' }}>
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

        {canEdit && (
          <BulkSheet
            open={sheetOpen}
            onClose={() => setSheetOpen(false)}
            attendanceTypes={attendanceTypes}
            overwriteFilled={overwriteFilled}
            onOverwriteFilledChange={setOverwriteFilled}
            onBulkGrade={bulkSetGrade}
            onBulkAtt={bulkSetAtt}
            onBulkRemark={bulkSetRemark}
            onClearAll={clearAll}
            columns={columns}
          />
        )}

        {canEdit && (
          <ColumnsSettingsSheet
            open={columnsOpen}
            onClose={() => setColumnsOpen(false)}
            columns={columns}
            onToggle={toggleColumn}
          />
        )}
      </Flex>
    </Panel>
  );
};
