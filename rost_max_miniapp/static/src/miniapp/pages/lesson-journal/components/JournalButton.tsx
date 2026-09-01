import React from 'react';
import { Button } from '@vkontakte/vkui';
import {
  cycleGrade,
  cycleAttendance,
  getGradeDisplay,
  getAttendanceDisplay,
} from '@/shared/lib/cycle';
import type { AttendanceType } from '@/shared/lib/types';

type JournalButtonVariant = 'grade' | 'attendance' | 'bulk-grade' | 'bulk-attendance';

interface JournalButtonProps {
  kind: 'grade' | 'attendance';
  value: number | null;
  attendanceTypes?: AttendanceType[];
  onCycle?: (next: number | null) => void;
  title?: string;
  variant?: JournalButtonVariant;
  size?: 'm' | 'l';
}

const sizeByVariant: Record<JournalButtonVariant, 'm' | 'l'> = {
  grade: 'm',
  attendance: 'm',
  'bulk-grade': 'l',
  'bulk-attendance': 'l',
};

const JournalButton: React.FC<JournalButtonProps> = ({
  kind,
  value,
  attendanceTypes,
  onCycle,
  title,
  variant,
  size: propSize,
}) => {
  const v = variant ?? (kind === 'grade' ? 'grade' : 'attendance');
  const list = attendanceTypes ?? [];
  const next = kind === 'grade'
    ? cycleGrade(value)
    : cycleAttendance(value, list);
  const text = kind === 'grade'
    ? getGradeDisplay(value)
    : getAttendanceDisplay(value, list);
  const active = value != null;
  const appearance = active ? 'accent' : 'neutral';
  const mode = active ? 'primary' : 'tertiary';
  const size = propSize ?? sizeByVariant[v];

  return (
    <Button
      type="button"
      onClick={onCycle ? () => onCycle(next) : undefined}
      title={title}
      size={size}
      mode={mode}
      appearance={appearance}
      style={{ minWidth: 'auto', padding: 0,  minInlineSize: 'auto', paddingInline: 0 }}
    >
      {text}
    </Button>
  );
};

export { JournalButton };
export type { JournalButtonProps, JournalButtonVariant };