import React from 'react';
import { Flex, List, Text, Button } from '@vkontakte/vkui';
import { StudentRow } from './StudentRow';
import { EmptyState } from '@/shared/components/EmptyState';
import type { Student, AttendanceType, GradeField, JournalColumns } from '@/shared/lib/types';

interface LessonJournalContentProps {
  loading: boolean;
  error: string | null;
  students: Student[];
  attendanceTypes: AttendanceType[];
  columns: JournalColumns;
  canEdit?: boolean;
  onCycleGrade?: (student: Student, field: GradeField, next: number | null) => void;
  onCycleAttendance?: (student: Student, next: number | null) => void;
  onRemarkChange?: (student: Student, remark: string) => void;
  onRetry?: () => void;
}

/** Контент журнала: загрузка / ошибка / пустое состояние / список студентов */
export const LessonJournalContent: React.FC<LessonJournalContentProps> = ({
  loading,
  error,
  students,
  attendanceTypes,
  columns,
  canEdit = true,
  onCycleGrade,
  onCycleAttendance,
  onRemarkChange,
  onRetry,
}) => {
  if (loading) {
    return (
      <Flex height="200px" align="center" justify="center">
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
    <List gap={12} style={{width: '100%'}}>
      {students.map((student) => (
        <StudentRow
          key={student.id}
          student={student}
          attendanceTypes={attendanceTypes}
          canEdit={canEdit}
          columns={columns}
          onCycleGrade={onCycleGrade}
          onCycleAttendance={onCycleAttendance}
          onRemarkChange={onRemarkChange}
        />
      ))}
    </List>
  );
};
