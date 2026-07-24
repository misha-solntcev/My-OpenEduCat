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

// Простые дефолты для каждого варианта (в пикселях/строках)
const VARIANT_DEFAULTS: Record<JournalButtonVariant, Partial<JournalButtonProps>> = {
  'grade': {
    height: 34,
    minWidth: 30,
    fontSize: 15,
    lineHeight: 1,
    padding: '0 6px',
  },
  'attendance': {
    height: 34,
    minWidth: 34,
    fontSize: 12,
    lineHeight: 1,
    padding: '0 10px',
    whiteSpace: 'nowrap',
  },
  'bulk-grade': {
    height: 40,
    minWidth: 38,
    fontSize: 15,
    lineHeight: 1,
    padding: '0 6px',
  },
  'bulk-attendance': {
    height: 40,
    minWidth: 34,
    fontSize: 12,
    lineHeight: 1,
    padding: '0 10px',
    whiteSpace: 'nowrap',
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
  const defaults = VARIANT_DEFAULTS[v];

  // Применяем дефолты варианта, затем переопределения из пропсов
  const finalHeight = height ?? defaults.height;
  const finalMinWidth = minWidth ?? defaults.minWidth;
  const finalFontSize = fontSize ?? defaults.fontSize;
  const finalLineHeight = lineHeight ?? defaults.lineHeight;
  const finalPadding = padding ?? defaults.padding;
  const finalWhiteSpace = whiteSpace ?? defaults.whiteSpace;

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
        height: finalHeight,
        minWidth: finalMinWidth,
        fontSize: finalFontSize,
        lineHeight: finalLineHeight,
        padding: finalPadding,
        whiteSpace: finalWhiteSpace,
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