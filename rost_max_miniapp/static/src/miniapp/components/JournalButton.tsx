import React from 'react';
import { 
  cycleGrade, 
  cycleAttendance, 
  getGradeDisplay, 
  getAttendanceDisplay,
  getGradeColor,
  getAttendanceColor 
} from '@/lib/cycle';
import type { AttendanceType } from '@/lib/types';

type JournalButtonVariant = 
  | 'grade'           
  | 'attendance'      
  | 'bulk-grade'      
  | 'bulk-attendance'; 

interface JournalButtonProps {
  kind: 'grade' | 'attendance';
  value: number | null;
  attendanceTypes?: AttendanceType[];
  onCycle: (next: number | null) => void;
  title?: string;
  variant?: JournalButtonVariant;
  height?: number;
  minWidth?: number;
  fontSize?: number;
  lineHeight?: number;
  padding?: string;
  whiteSpace?: string;
  flex?: number;
}

// CSS custom property map for each variant
const VARIANT_CSS_VARS: Record<JournalButtonVariant, Record<string, string>> = {
  'grade': {
    '--jb-height': 'var(--jb-grade-height)',
    '--jb-min-width': 'var(--jb-grade-min-width)',
    '--jb-font-size': 'var(--jb-grade-font-size)',
    '--jb-padding': 'var(--jb-grade-padding)',
  },
  'attendance': {
    '--jb-height': 'var(--jb-attendance-height)',
    '--jb-min-width': 'var(--jb-attendance-min-width)',
    '--jb-font-size': 'var(--jb-attendance-font-size)',
    '--jb-padding': 'var(--jb-attendance-padding)',
    '--jb-white-space': 'var(--jb-attendance-white-space)',
  },
  'bulk-grade': {
    '--jb-height': 'var(--jb-bulk-grade-height)',
    '--jb-min-width': 'var(--jb-bulk-grade-min-width)',
    '--jb-font-size': 'var(--jb-bulk-grade-font-size)',
    '--jb-padding': 'var(--jb-bulk-grade-padding)',
  },
  'bulk-attendance': {
    '--jb-height': 'var(--jb-bulk-attendance-height)',
    '--jb-min-width': 'var(--jb-bulk-attendance-min-width)',
    '--jb-font-size': 'var(--jb-bulk-attendance-font-size)',
    '--jb-padding': 'var(--jb-bulk-attendance-padding)',
    '--jb-white-space': 'var(--jb-bulk-attendance-white-space)',
  },
};

const JournalButton: React.FC<JournalButtonProps> = ({
  kind,
  value,
  attendanceTypes,
  onCycle,
  title,
  variant,
  height,
  minWidth,
  fontSize,
  lineHeight,
  padding,
  whiteSpace,
  flex,
}) => {
  const defaultVariant: JournalButtonVariant = kind === 'grade' ? 'grade' : 'attendance';
  const v = variant ?? defaultVariant;
  const cssVars = VARIANT_CSS_VARS[v];

  const list = attendanceTypes ?? [];
  const next = kind === 'grade'
    ? cycleGrade(value)
    : cycleAttendance(value, list);
  const text = kind === 'grade'
    ? getGradeDisplay(value)
    : getAttendanceDisplay(value, list);
  const active = value != null;
  const activeColor = kind === 'grade'
    ? getGradeColor(value)
    : getAttendanceColor(list.find(t => t.id === value)?.name);

  return (
    <button
      type="button"
      onClick={() => onCycle(next)}
      title={title}
      className={`rm-journal-btn ${active ? 'rm-journal-btn--active' : ''}`}
      style={{
        height: height ? `${height}px` : cssVars['--jb-height'],
        minWidth: minWidth ? `${minWidth}px` : cssVars['--jb-min-width'],
        fontSize: fontSize ? `${fontSize}px` : cssVars['--jb-font-size'],
        lineHeight,
        padding: padding ?? cssVars['--jb-padding'],
        whiteSpace: whiteSpace ?? cssVars['--jb-white-space'],
        flex,
        ...(active ? ({ ['--jb-color' as string]: activeColor } as React.CSSProperties) : null),
      }}
    >
      {text}
    </button>
  );
};

export { JournalButton };
export type { JournalButtonProps, JournalButtonVariant };