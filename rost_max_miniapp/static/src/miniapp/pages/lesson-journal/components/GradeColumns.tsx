import React from 'react';
import { Flex } from '@vkontakte/vkui';
import { JournalButton } from './JournalButton';
import { GRADE_FIELDS } from '@/shared/lib/colors';
import type { GradeField, AttendanceType } from '@/shared/lib/types';

interface GradeColumnsProps {
  gradeValues: Record<GradeField, number | null>;
  onCycleGrade: (field: GradeField, next: number | null) => void;
  gradeVariant: 'grade' | 'attendance' | 'bulk-grade' | 'bulk-attendance';
  attendanceValue?: number | null;
  onCycleAttendance?: (next: number | null) => void;
  attendanceVariant?: 'grade' | 'attendance' | 'bulk-grade' | 'bulk-attendance';
  attendanceTypes?: AttendanceType[];
  attendanceTitle?: string;
}

/** Колонка с тремя оценками + посещаемостью (используется в StudentRow и BulkSheet) */
export const GradeColumns: React.FC<GradeColumnsProps> = ({
  gradeValues,
  onCycleGrade,
  gradeVariant,
  attendanceValue = null,
  onCycleAttendance,
  attendanceVariant,
  attendanceTypes = [],
  attendanceTitle,
}) => (
  <Flex gap={4} wrap="wrap" minInlineSize={0}>
    {GRADE_FIELDS.map((field) => (
      <JournalButton
        key={field}
        kind="grade"
        value={gradeValues[field]}
        onCycle={(next) => onCycleGrade(field, next)}
        title={`Оценка ${field === 'grade_1' ? 'О1' : field === 'grade_2' ? 'О2' : 'О3'}`}
        variant={gradeVariant}
        size="s"
      />
    ))}

    {onCycleAttendance && (
      <JournalButton
        kind="attendance"
        value={attendanceValue}
        attendanceTypes={attendanceTypes}
        onCycle={onCycleAttendance}
        title={attendanceTitle ?? 'Нажмите, чтобы сменить отметку посещаемости'}
        variant={attendanceVariant ?? 'attendance'}
        size="s"
      />
    )}
  </Flex>
);