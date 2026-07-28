import React from 'react';
import { Flex, Text } from '@vkontakte/vkui';
import { StudentRow } from '@/components/StudentRow';
import { EmptyState } from '@/components/EmptyState';
import type { Student, AttendanceType, GradeField } from '@/lib/types';

interface LessonJournalContentProps {
  loading: boolean;
  students: Student[];
  attendanceTypes: AttendanceType[];
  onCycleGrade: (student: Student, field: GradeField, next: number | null) => void;
  onCycleAttendance: (student: Student, next: number | null) => void;
}

/** Контент журнала: загрузка / пустое состояние / список студентов */
export const LessonJournalContent: React.FC<LessonJournalContentProps> = ({
  loading,
  students,
  attendanceTypes,
  onCycleGrade,
  onCycleAttendance,
}) => {
  if (loading) {
    return (
      <Flex align="center" justify="center" style={{ flex: 1, minHeight: '200px' }}>
        <Text weight="2" style={{ color: 'var(--vkui--color_text_secondary)' }}>Загрузка...</Text>
      </Flex>
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