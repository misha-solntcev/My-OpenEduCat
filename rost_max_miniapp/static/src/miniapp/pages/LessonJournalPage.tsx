import React from 'react';
import { Flex, Typography, IconButton, Button } from '@maxhub/max-ui';
import { StudentRow } from '@/components/StudentRow';
import { BulkSheet } from '@/components/BulkSheet';
import { useLessonJournal } from '@/hooks/useLessonJournal';
import { useBulkSheet } from '@/hooks/useBulkSheet';
import { Zap } from 'lucide-react';
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
    overwriteAll,
    setOverwriteAll,
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

  const headerTitle = lesson ? (lesson.subject || 'Журнал оценок') : 'Журнал оценок';
  const headerSubtitle = lesson ? [lesson.batch, lesson.timing].filter(Boolean).join(' · ') : '';

  const header = (
    <Flex direction="column" gap={2} style={{ padding: '12px 16px', borderBottom: '1px solid var(--stroke-separator-secondary)', backgroundColor: 'var(--background-surface-card)', flexShrink: 0 }}>
      <Flex align="center" gap={12} style={{ width: '100%' }}>
        <IconButton appearance="themed" mode="tertiary" onClick={handleBack}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </IconButton>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Typography.Title variant="small-strong">
            {headerTitle}
          </Typography.Title>
        </div>
        <IconButton appearance="themed" mode="tertiary" onClick={() => { baselineRef.current = students.map(s => ({ ...s })); setSheetOpen(true); }} title="Массово проставить оценки и посещаемость" style={{ flexShrink: 0 }}>
          <Zap size={20} color="currentColor" />
        </IconButton>
      </Flex>
      {headerSubtitle && (
        <Typography.Label variant="small-strong" style={{ marginLeft: '36px', color: 'var(--text-secondary)' }}>
          {headerSubtitle}
        </Typography.Label>
      )}
    </Flex>
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
      <Flex
        direction="column"
        align="center"
        justify="center"
        className="rm-card rm-card--empty"
        style={{
          paddingBottom: '24px'
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '12px' }}>🍃</div>
        <Typography.Title>
          Ученики не найдены
        </Typography.Title>
        <Typography.Body style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>
          Для этого урока ещё не сформирован список посещаемости.
        </Typography.Body>
      </Flex>
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
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          WebkitOverflowScrolling: 'touch',
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(128, 128, 128, 0.4) transparent',
          backgroundColor: 'var(--background-surface-ground)',
          paddingTop: '16px',
          paddingBottom: dirty ? '84px' : '24px'
        }}
      >
        <div style={{ paddingLeft: '16px', paddingRight: '16px' }}>
          {content}
        </div>
      </div>

      {dirty && (
        <div
          style={{
            position: 'fixed',
            left: 0,
            right: 0,
            bottom: 0,
            padding: '12px 16px calc(12px + env(safe-area-inset-bottom))',
            backgroundColor: 'var(--background-surface-card)',
            borderTop: '1px solid var(--stroke-separator-secondary)',
            zIndex: 90,
          }}
        >
        <Button
          stretched
          size="large"
          mode="primary"
          appearance="themed"
          loading={saving}
          onClick={saveAll}
        >
          Сохранить
        </Button>
      </div>
      )}

      {showExitBanner && (
        <div
          onClick={() => setShowExitBanner(false)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 200,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: '360px',
              backgroundColor: 'var(--background-surface-card)',
              borderRadius: '16px',
              padding: '20px 16px calc(16px + env(safe-area-inset-bottom))',
              boxSizing: 'border-box',
            }}
          >
            <div style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', color: 'var(--text-primary)' }}>
              Сохранить изменения?
            </div>
            <Flex direction="column" gap={10} style={{ width: '100%' }}>
              <Button
                stretched
                size="large"
                mode="primary"
                appearance="themed"
                loading={saving}
                onClick={exitSave}
              >
                Да, сохранить
              </Button>
              <Button
                stretched
                size="large"
                mode="secondary"
                loading={saving}
                onClick={exitDiscard}
              >
                Нет, не сохранять
              </Button>
              <Button
                stretched
                size="large"
                mode="tertiary"
                onClick={() => setShowExitBanner(false)}
              >
                Остаться
              </Button>
            </Flex>
          </div>
        </div>
      )}

      {sheetOpen && (
        <BulkSheet
          students={students}
          attendanceTypes={attendanceTypes}
          overwriteAll={overwriteAll}
          onOverwriteAllChange={setOverwriteAll}
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