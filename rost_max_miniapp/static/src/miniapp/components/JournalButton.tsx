import React from 'react';
import { gradeColor, attendanceColor, GRADES } from '@/lib/colors';
import type { AttendanceType } from '@/lib/types';

type JournalButtonVariant = 
  | 'grade'           // оценка в строке студента (30px minWidth, padding 0 6px)
  | 'attendance'      // посещаемость в строке студента (12px font, 34px minWidth)
  | 'bulk-grade'      // оценка в шторке (38px minWidth, 40px height)
  | 'bulk-attendance'; // посещаемость в шторке (12px font, 34px minWidth, 40px height)

interface JournalButtonProps {
  kind: 'grade' | 'attendance';
  value: number | null;
  // Нужны только для kind="attendance": список типов посещаемости для цикла и отображения имени
  attendanceTypes?: AttendanceType[];
  onCycle: (next: number | null) => void;
  title?: string;
  // Вариант визуального представления (заменяет кучу стилевых пропсов)
  variant?: JournalButtonVariant;
  // Переопределения (опционально, для нестандартных случаев)
  height?: number;
  minWidth?: number;
  fontSize?: number;
  lineHeight?: number;
  padding?: string;
  whiteSpace?: string;
  flex?: number;
}

// Варианты по умолчанию
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

// Самодостаточная кнопка-карусель оценки/посещаемости.
// Сама крутит значение по кругу (GRADES для оценок, attendanceTypes для
// посещаемости), сама считает активность и акцентный цвет, отдаёт родителю
// уже готовое следующее значение через onCycle(next: number|null).
// Акцентный цвет передаём через inline CSS-переменную --jb-color
// (см. .rm-journal-btn--active в style.css), чтобы color-mix мог сделать
// валидный полупрозрачный фон.
const JournalButton: React.FC<JournalButtonProps> = ({
  kind,
  value,
  attendanceTypes,
  onCycle,
  title,
  variant,
  // Переопределения
  height,
  minWidth,
  fontSize,
  lineHeight,
  padding,
  whiteSpace,
  flex,
}) => {
  // Определяем вариант по умолчанию на основе kind
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

  let text: string;
  let active: boolean;
  let activeColor: string;
  let next: number | null;

  if (kind === 'grade') {
    const idx = GRADES.indexOf(value != null ? String(value) : '');
    const nextRaw = GRADES[(idx + 1) % GRADES.length];
    next = nextRaw === '' ? null : Number(nextRaw);
    text = value != null ? String(value) : '—';
    active = value != null;
    activeColor = gradeColor(value);
  } else {
    const list = attendanceTypes ?? [];
    if (list.length === 0) {
      next = null;
      text = '—';
      active = false;
      activeColor = 'var(--text-secondary)';
    } else {
      const curIdx = list.findIndex(t => t.id === value);
      const nextType = list[(curIdx + 1) % list.length];
      next = nextType.id;
      const cur = list.find(t => t.id === value);
      text = cur?.name ?? '—';
      active = value != null;
      activeColor = attendanceColor(cur?.name);
    }
  }

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
        padding: finalPadding ?? '0',
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