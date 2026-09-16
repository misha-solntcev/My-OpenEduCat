import React from 'react';
import {
  cycleGrade,
  cycleAttendance,
  getGradeDisplay,
  getAttendanceDisplay,
  getGradeAppearance,
  getAttendanceAppearance,
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

/** Цветовая карта (утверждена Мишей 2026-09-15):
 *  зелёный  = Присутствует, Дистанционно, оценка 5;
 *  синий    = Опоздал, оценка 4;
 *  янтарный = Болеет, Уважительная причина, оценка 3;
 *  красный  = оценка 2.
 *  Чёрной заливки (neutral primary) больше нет.
 *  Токены VKUI сами подменяются в тёмной теме — ноль своего CSS. */
type Tone = {
  bg: string;      // тинт-заливка
  border: string;  // тонкая рамка того же цвета
  text: string;    // цветной текст
  dot: string;     // базовый цвет точки
};

const toneByAppearance = (appearance: 'positive' | 'accent' | 'warning' | 'negative'): Tone => {
  switch (appearance) {
    case 'positive':
      return {
        bg: 'var(--vkui--color_background_positive_tint)',
        border: 'var(--vkui--color_stroke_positive)',
        text: 'var(--vkui--color_text_positive)',
        dot: 'var(--vkui--color_background_positive)',
      };
    case 'accent':
      return {
        bg: 'var(--vkui--color_background_accent_tint)',
        border: 'var(--vkui--color_stroke_accent)',
        text: 'var(--vkui--color_text_accent)',
        dot: 'var(--vkui--color_background_accent)',
      };
    case 'warning':
      // warning-тинта в VKUI нет, но есть background_warning —
      // в light #fff2d6, в dark #473315 (сами токены темизируются).
      return {
        bg: 'var(--vkui--color_background_warning)',
        border: 'var(--vkui--color_icon_warning)',
        text: 'var(--vkui--color_text_primary)',
        dot: 'var(--vkui--color_icon_warning)',
      };
    case 'negative':
      return {
        bg: 'var(--vkui--color_background_negative_tint)',
        border: 'var(--vkui--color_stroke_negative)',
        text: 'var(--vkui--color_text_negative)',
        dot: 'var(--vkui--color_background_negative)',
      };
  }
};

/** Пустое состояние: пунктирная рамка, «—», серый, участвует в тап-цикле. */
const emptyStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1.5px dashed var(--vkui--color_icon_secondary)',
  color: 'var(--vkui--color_text_secondary)',
};

const baseButtonStyle = (size: 'm' | 'l'): React.CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 6,
  height: size === 'l' ? 36 : 32,
  minWidth: 32,
  borderRadius: 10,
  fontSize: 13,
  fontWeight: 600,
  whiteSpace: 'nowrap',
  cursor: 'pointer',
});

const dotStyle = (color: string): React.CSSProperties => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  flexShrink: 0,
  background: color,
});

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
  const appearance = kind === 'grade'
    ? getGradeAppearance(value)
    : getAttendanceAppearance(list.find(t => t.id === value)?.name);
  const size = propSize ?? sizeByVariant[v];

  if (!active) {
    return (
      <button
        type="button"
        onClick={onCycle ? () => onCycle(next) : undefined}
        title={title}
        style={{ ...baseButtonStyle(size), padding: '0 10px', ...emptyStyle }}
      >
        {text}
      </button>
    );
  }

  const tone = toneByAppearance(appearance);
  // Точка только у текстовых кнопок посещаемости (у «5»/«—» она не нужна).
  const showDot = kind === 'attendance';

  return (
    <button
      type="button"
      onClick={onCycle ? () => onCycle(next) : undefined}
      title={title}
      style={{
        ...baseButtonStyle(size),
        padding: showDot ? '0 10px' : 0,
        background: tone.bg,
        border: `1px solid ${tone.border}`,
        color: tone.text,
      }}
    >
      {showDot && <span style={dotStyle(tone.dot)} />}
      {text}
    </button>
  );
};

export { JournalButton };
export type { JournalButtonProps, JournalButtonVariant };
