import React from 'react';
import { Flex, Text, Button } from '@vkontakte/vkui';
import { StudentRow } from './StudentRow';
import { EmptyState } from '@/shared/components';
import type { Student, AttendanceType, GradeField } from '@/lib/types';

interface LessonJournalContentProps {
  loading: boolean;
  error: string | null;
  students: Student[];
  attendanceTypes: AttendanceType[];
  onCycleGrade: (student: Student, field: GradeField, next: number | null) => void;
  onCycleAttendance: (student: Student, next: number | null) => void;
  onRetry?: () => void;
}

/** Контент журнала: загрузка / ошибка / пустое состояние / список студентов */
export const LessonJournalContent: React.FC<LessonJournalContentProps> = ({
  loading,
  error,
  students,
  attendanceTypes,
  onCycleGrade,
  onCycleAttendance,
  onRetry,
}) => {
  if (loading) {
    return (
      <Flex align="center" justify="center" style={{ flex: 1, minHeight: '200px' }}>
        <Text weight="2">Загрузка...</Text>
      </Flex>
    );
  }

  if (error) {
    return (
      <EmptyState
        title="Ошибка загрузки"
        subtitle={error}
        action={onRetry ? <Button size="l" mode="primary" onClick={onRetry}>Повторить</Button> : undefined}
      />
    );
  }

  if (students.length === 0) {
    return (
      <EmptyState
        title="Ученики не найдены"
        subtitle="Для этого урока ещё не сформирован список посещаемости."
      />
    );
  }

  return (
    <Flex direction="column" gap={12} style={{ width: '100%' }}>
      {students.map((student) => (
        <StudentRow
          key={student.id}
          student={student}
          attendanceTypes={attendanceTypes}
          onCycleGrade={onCycleGrade}
          onCycleAttendance={onCycleAttendance}
        />
      ))}
    </Flex>
  );
};