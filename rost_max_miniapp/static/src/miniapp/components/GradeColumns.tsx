import React from 'react';
import { Flex } from '@vkontakte/vkui';
import { JournalButton } from '@/components/JournalButton';
import { GRADE_FIELDS } from '@/lib/colors';
import type { GradeField, AttendanceType } from '@/lib/types';

interface GradeColumnsProps {
  gradeValues: Record<GradeField, number | null>;
  onCycleGrade: (field: GradeField, next: number | null) => void;
  gradeVariant: 'grade' | 'attendance' | 'bulk-grade' | 'bulk-attendance';
  attendanceValue?: number | null;
  onCycleAttendance?: (next: number | null) => void;
  attendanceVariant?: 'grade' | 'attendance' | 'bulk-grade' | 'bulk-attendance';
  attendanceTypes?: AttendanceType[];
  gradeTitlePrefix?: string;
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
  gradeTitlePrefix,
  attendanceTitle,
}) => (
  <Flex gap={6} wrap="wrap">
    {GRADE_FIELDS.map((field) => (
      <JournalButton
        key={field}
        kind="grade"
        value={gradeValues[field]}
        onCycle={(next) => onCycleGrade(field, next)}
        title={`${gradeTitlePrefix ?? 'Оценка'} ${field === 'grade_1' ? 'О1' : field === 'grade_2' ? 'О2' : 'О3'}`}
        variant={gradeVariant}
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
      />
    )}
  </Flex>
);