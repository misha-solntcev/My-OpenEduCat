import React from 'react';
import { gradeColor, attendanceColor, GRADES } from '../../lib/colors';
import type { AttendanceType } from '../../lib/types';

interface JournalButtonProps {
  kind: 'grade' | 'attendance';
  value: number | null;
  // Нужны только для kind="attendance": список типов посещаемости для цикла и отображения имени
  attendanceTypes?: AttendanceType[];
  onCycle: (next: number | null) => void;
  title?: string;
  height?: number;
  minWidth?: number;
  fontSize?: number;
  lineHeight?: number;
  padding?: string;
  whiteSpace?: string;
  flex?: number;
}

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
  height = 34,
  minWidth = 34,
  fontSize = 15,
  lineHeight = 1,
  padding,
  whiteSpace,
  flex,
}) => {
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
    const curIdx = list.findIndex(t => t.id === value);
    const nextType = list[(curIdx + 1) % list.length];
    next = nextType.id;
    const cur = list.find(t => t.id === value);
    text = cur?.name ?? '—';
    active = value != null;
    activeColor = attendanceColor(cur?.name);
  }

  return (
    <button
      type="button"
      onClick={() => onCycle(next)}
      title={title}
      className={`rm-journal-btn ${active ? 'rm-journal-btn--active' : ''}`}
      style={{
        height,
        minWidth,
        fontSize,
        lineHeight,
        padding: padding ?? '0',
        whiteSpace,
        flex,
        ...(active ? ({ ['--jb-color' as string]: activeColor } as React.CSSProperties) : null),
      }}
    >
      {text}
    </button>
  );
};

export { JournalButton };
export type { JournalButtonProps };
