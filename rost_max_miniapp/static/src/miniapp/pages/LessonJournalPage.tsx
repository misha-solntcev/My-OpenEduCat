import React from 'react';
import { Flex } from '@maxhub/max-ui';
import { StudentRow } from '@/components/StudentRow';
import { BulkSheet } from '@/components/BulkSheet';
import { ExitBanner } from '@/components/ExitBanner';
import { LessonHeader } from '@/components/LessonHeader';
import { SaveBar } from '@/components/SaveBar';
import { EmptyState } from '@/components/EmptyState';
import { useLessonJournal } from '@/hooks/useLessonJournal';
import { useBulkSheet } from '@/hooks/useBulkSheet';
import type { GradeField } from '@/lib/colors';

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
  // Колбэки для синхронизации с локальным буфером (useLessonJournal)
  const bulkSetGrade = (field: GradeField, value: number | null) => {
    bulkSetGradeLocal(field, value);
  };
  const bulkSetAtt = (attId: number | null) => {
    bulkSetAttLocal(attId);
  };
  const clearAll = () => {
    clearAllLocal();
  };

  const {
    overwriteFilled,
    setOverwriteFilled,
    baselineRef,
    firstEditable,
    // useBulkSheet внутри вызывает наши bulkSetGrade/bulkSetAtt/clearAll
    // которые обновляют локальный буфер через useLessonJournal
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
    baselineRef.current = students.map(s => ({ ...s }));
    setSheetOpen(true);
  };

  const header = (
    <LessonHeader
      lesson={lesson}
      onBack={handleBack}
      onOpenBulkSheet={onOpenBulkSheet}
    />
  );

  let content: React.ReactNode;
  if (loading) {
    content = (
      <Flex align="center" justify="center" style={{ flex: 1, minHeight: '200px' }}>
        <div style={{ color: 'var(--text-secondary)' }}>Загрузка...</div>
      </Flex>
    );
  } else if (students.length === 0) {
    content = (
      <EmptyState
        title="Ученики не найдены"
        subtitle="Для этого урока ещё не сформирован список посещаемости."
      />
    );
  } else {
    content = (
      <Flex direction="column" gap={12} style={{ width: '100%' }}>
        {students.map((student) => (
          <StudentRow
            key={student.id}
            student={student}
            attendanceTypes={attendanceTypes}
            onCycleGrade={cycleGradeField}
            onCycleAttendance={cycleAttendance}
          />
        ))}
      </Flex>
    );
  }

  return (
    <Flex direction="column" align="stretch" style={{ width: '100%', height: '100dvh' }}>
      {header}
      <div className="rm-journal-scroll" style={{ paddingBottom: dirty ? '84px' : '24px' }}>
        <div className="rm-journal-content">
          {content}
        </div>
      </div>

      <SaveBar saving={saving} onSave={saveAll} />

      <ExitBanner
        visible={showExitBanner}
        onClose={() => setShowExitBanner(false)}
        onSave={exitSave}
        onDiscard={exitDiscard}
        saving={saving}
      />

      {sheetOpen && (
        <BulkSheet
          students={students}
          attendanceTypes={attendanceTypes}
          overwriteFilled={overwriteFilled}
          onOverwriteFilledChange={setOverwriteFilled}
          firstEditable={firstEditable}
          onBulkGrade={bulkSetGrade}
          onBulkAtt={bulkSetAtt}
          onClearAll={clearAll}
          onClose={() => setSheetOpen(false)}
        />
      )}
    </Flex>
  );
};