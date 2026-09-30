import React from 'react';
import { Box, Flex, Panel, Button } from '@vkontakte/vkui';
import { BulkSheet } from '@/pages/lesson-journal/components/BulkSheet';
import { ColumnsSettingsSheet } from '@/pages/lesson-journal/components/ColumnsSettingsSheet';
import { TopicHomeworkCard } from '@/pages/lesson-journal/components/TopicHomeworkCard';
import { LessonJournalContent } from '@/pages/lesson-journal/components/LessonJournalContent';
import { shortBatchName } from '@/shared/components/LessonRow';
import { LessonJournalToolbar } from '@/pages/lesson-journal/components/LessonJournalToolbar';
import { useLessonJournal } from '@/pages/lesson-journal/hooks/useLessonJournal';
import { useBulkSheet } from '@/pages/lesson-journal/hooks/useBulkSheet';
import type { GradeField } from '@/shared/lib/types';

/** Фильтр-задание для входа в «Задания» из журнала урока. */
export interface LessonHomeworkFilter {
  /** Класс БЕЗ учебного года, как в ленте заданий: бэк отдаёт
   *  op.batch.name через _batch_short («7 А  2026/2027» -> «7 А»).
   *  Сырое имя из урока здесь не подошло бы — чип фильтра не совпал бы
   *  со значением из ленты и фильтр отсёк бы все задания. */
  batch: string;
  /** Название предмета (op.subject.name). */
  subject: string;
}

interface LessonJournalPageProps {
  id: string;
  lessonId: number | null;
  onBack: () => void;
  /** Переход на вкладку «Задания» с фильтром по предмету и классу урока. */
  onOpenHomework: (filter: LessonHomeworkFilter) => void;
}

export const LessonJournalPage: React.FC<LessonJournalPageProps> = ({ id, lessonId, onBack, onOpenHomework }) => {
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
    setAnswerRequired,
    setAssignmentId,
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

  // Вход на «Задания» из карточки темы. Класс режем через shortBatchName:
  // лента заданий отдаёт batch уже без года (op.batch.name через
  // _batch_short), и без среза фильтр не совпал бы с классом урока.
  const openHomework = () => {
    if (!lesson) return;
    onOpenHomework({
      batch: shortBatchName(lesson.batch),
      subject: lesson.subject,
    });
  };

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
                lessonId={lessonId}
                canEdit={canEdit}
                onTopicChange={setTopic}
                onHomeworkChange={setHomework}
                onAnswerRequiredChange={setAnswerRequired}
                onAssignmentCreated={setAssignmentId}
                onCheckHomework={canEdit ? openHomework : undefined}
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
            hwEnabled={false}
            onCycleGrade={cycleGradeField}
            onCycleAttendance={cycleAttendance}
            onRemarkChange={setRemark}
          />
        </Box>

        {canEdit && dirty && (
          <Box position="sticky" insetBlockEnd={0} padding="m" paddingInline="l" style={{ borderTop: '1px solid var(--vkui--color_separator_primary)', backgroundColor: 'var(--vkui--color_background_content)', zIndex: 'var(--vkui--z_index_popout)' }}>
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
            // Молния (массовые операции) о ДЗ не знает: оценки за ДЗ ставятся
            // только в задании. Передаём hwEnabled={false}, иначе BulkSheet
            // со своим дефолтом =true нарисовал бы кнопки ДЗ 1 / ДЗ 2.
            hwEnabled={false}
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
