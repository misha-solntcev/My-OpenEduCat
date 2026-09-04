import React from 'react';
import { Flex } from '@vkontakte/vkui';
import { JournalButton } from './JournalButton';
import { GRADE_FIELDS } from '@/shared/lib/colors';
import type { GradeField, AttendanceType, JournalColumns } from '@/shared/lib/types';

interface GradeColumnsProps {
  gradeValues: Record<GradeField, number | null>;
  onCycleGrade?: (field: GradeField, next: number | null) => void;
  gradeVariant: 'grade' | 'attendance' | 'bulk-grade' | 'bulk-attendance';
  attendanceValue?: number | null;
  onCycleAttendance?: (next: number | null) => void;
  attendanceVariant?: 'grade' | 'attendance' | 'bulk-grade' | 'bulk-attendance';
  attendanceTypes?: AttendanceType[];
  attendanceTitle?: string;
  gradeTitlePrefix?: string;
  /** Персональная настройка колонок: О2/О3 выключенные не рендерятся. */
  columns?: JournalColumns;
}

/** Колонка с оценками + посещаемостью (StudentRow и BulkSheet).
 *  grade_1 и attendance показываются всегда, О2/О3 — по настройке. */
export const GradeColumns: React.FC<GradeColumnsProps> = ({
  gradeValues,
  onCycleGrade,
  gradeVariant,
  attendanceValue = null,
  onCycleAttendance,
  attendanceVariant,
  attendanceTypes = [],
  attendanceTitle,
  gradeTitlePrefix,
  columns,
}) => {
  const visible = (f: GradeField) =>
    !columns || f === 'grade_1' || Boolean(columns[f]);

  return (
    <Flex gap={4} wrap="wrap" minInlineSize={0}>
      {GRADE_FIELDS.filter(visible).map((field) => (
        <JournalButton
          key={field}
          kind="grade"
          value={gradeValues[field]}
          onCycle={onCycleGrade ? (next) => onCycleGrade(field, next) : undefined}
          title={`${gradeTitlePrefix ?? 'Оценка'} ${field === 'grade_1' ? 'О1' : field === 'grade_2' ? 'О2' : 'О3'}`}
          variant={gradeVariant}
          size="m"
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
          size="m"
        />
      )}
    </Flex>
  );
};
