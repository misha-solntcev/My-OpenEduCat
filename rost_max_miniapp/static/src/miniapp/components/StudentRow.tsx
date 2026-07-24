import React from 'react';
import { Flex, Avatar, EllipsisText } from '@vkontakte/vkui';
import { GradeColumns } from '@/components/GradeColumns';
import { initialsOf } from '@/lib';
import type { Student, AttendanceType, GradeField } from '@/lib/types';

interface StudentRowProps {
  student: Student;
  attendanceTypes: AttendanceType[];
  onCycleGrade: (student: Student, field: GradeField, next: number | null) => void;
  onCycleAttendance: (student: Student, next: number | null) => void;
}

// Строка списка учеников: аватар + ФИО (обрезается) + карусели оценок
// и посещаемости. Карточка (.rm-card--row) задаётся снаружи через className.
// Вся логика цикла и цвета инкапсулирована в JournalButton.
export const StudentRow: React.FC<StudentRowProps> = ({
  student,
  attendanceTypes,
  onCycleGrade,
  onCycleAttendance,
}) => (
  <div className="rm-card rm-card--row">
    <Flex align="center" gap={12} style={{ width: '100%', minWidth: 0 }}>
      {/* Колонка 1: аватар (общий для двух строк) */}
      <Avatar
        size={40}
        initials={initialsOf(student.name)}
        src={student.avatar}
      />

      {/* Колонка 2: две строки */}
      <Flex direction="column" gap={6} style={{ flex: 1, minWidth: 0 }}>
        {/* Строка 1: ФИО без нумерации */}
        <EllipsisText maxLines={1} style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {student.name}
        </EllipsisText>

        {/* Строка 2: три оценки + посещаемость через GradeColumns */}
        <GradeColumns
          gradeValues={{
            grade_1: student.grade_1,
            grade_2: student.grade_2,
            grade_3: student.grade_3,
          }}
          onCycleGrade={(field, next) => onCycleGrade(student, field, next)}
          gradeVariant="grade"
          attendanceValue={student.attendance_type_id}
          onCycleAttendance={(next) => onCycleAttendance(student, next)}
          attendanceVariant="attendance"
          attendanceTypes={attendanceTypes}
        />
      </Flex>
    </Flex>
  </div>
);