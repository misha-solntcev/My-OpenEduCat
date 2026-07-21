import React from 'react';
import { Flex, Avatar, EllipsisText } from '@maxhub/max-ui';
import { JournalButton } from '../JournalButton';
import { GRADE_FIELDS, GRADE_FIELD_LABELS } from '../../lib/colors';
import { initialsOf } from '../../lib';
import type { Student, AttendanceType, GradeField } from '../../lib/types';

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
      <Avatar.Container size={40} form="squircle">
        <Avatar.Image
          src={student.avatar}
          fallback={<Avatar.Text>{initialsOf(student.name)}</Avatar.Text>}
        />
      </Avatar.Container>

      {/* Колонка 2: две строки */}
      <Flex direction="column" gap={6} style={{ flex: 1, minWidth: 0 }}>
        {/* Строка 1: ФИО без нумерации */}
        <EllipsisText maxLines={1} style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {student.name}
        </EllipsisText>

        {/* Строка 2: три оценки + посещаемость */}
        <Flex align="center" gap={6} wrap="wrap" style={{ width: '100%' }}>
          {GRADE_FIELDS.map((field) => (
            <JournalButton
              key={field}
              kind="grade"
              value={student[field]}
              onCycle={(next) => onCycleGrade(student, field, next)}
              title={`Оценка ${GRADE_FIELD_LABELS[field]}`}
              minWidth={30}
              padding="0 6px"
            />
          ))}

          <JournalButton
            kind="attendance"
            value={student.attendance_type_id}
            attendanceTypes={attendanceTypes}
            onCycle={(next) => onCycleAttendance(student, next)}
            title="Нажмите, чтобы сменить отметку посещаемости"
            fontSize={12}
            minWidth={34}
            padding="0 10px"
            whiteSpace="nowrap"
          />
        </Flex>
      </Flex>
    </Flex>
  </div>
);
