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

/** ЦВЕТА ОЦЕНОК И ПОСЕЩАЕМОСТИ — ЕДИНЫЙ ИСТОЧНИК ПРАВДЫ (Миша, 2026-09-15).
 *  Раньше карта жила приватно внутри JournalButton, а копии (`markTone` в
 *  HomeworkCardList, `gradeTone` в SubjectsPage) разъехались — оценки в разных
 *  экранах выглядели по-разному. Теперь цвет берут ОТСЮДА, отсюда же реэкспорт.
 *
 *  зелёный  = Присутствует, Дистанционно, оценка 5
 *  синий    = Опоздал, оценка 4
 *  янтарный = Болеет, Уважительная причина, оценка 3
 *  красный  = оценка 2
 *
 *  Текст на тинте — text_primary (адаптивный тёмный/светлый), НЕ цветной:
 *  цветной текст на своём тинте не читается ни в одной теме. Цвет несут
 *  фон и рамка. Токены VKUI подменяются в тёмной теме сами — ноль своего CSS. */
export type ToneAppearance = 'positive' | 'accent' | 'warning' | 'negative';

export type Tone = {
  bg: string;      // тинт-заливка
  border: string;  // тонкая рамка того же цвета
  text: string;    // цвет текста
  dot: string;     // базовый цвет точки
};

export const toneByAppearance = (appearance: ToneAppearance): Tone => {
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
        text: 'var(--vkui--color_text_primary)',
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

/** Тон оценки по значению (5/4/3/2; 0 или null — нейтральный серый). */
export const gradeTone = (mark: number | null | undefined): Tone => {
  if (!mark) {
    return {
      bg: 'var(--vkui--color_background_secondary)',
      border: 'var(--vkui--color_separator_primary)',
      text: 'var(--vkui--color_text_secondary)',
      dot: 'var(--vkui--color_icon_secondary)',
    };
  }
  return toneByAppearance(getGradeAppearance(mark));
};

/** Стили чипа оценки для мест, где нужна НЕ интерактивная кнопка
 *  (список предметов, сводка): рамка сплошная, как у JournalButton. */
export const gradeChipStyle = (mark: number): React.CSSProperties => {
  const tone = gradeTone(mark);
  return { background: tone.bg, borderColor: tone.border, color: tone.text };
};

/**
 * НЕинтерактивный чип оценки — единый вид во всём приложении:
 * список предметов ученика, карточки пары/ученика у учителя, сводка.
 * Раньше одинаковые чипы рисовались инлайном в трёх файлах и разъехались
 * по размеру и скруглению. Размеры — единственное место их правки.
 */
export const GradeChip: React.FC<{
  grade: number;
  /** s — 26px (ряды чипов), m — 30px (крупные сводки). */
  size?: 's' | 'm';
  title?: string;
}> = ({ grade, size = 's', title }) => (
  <span
    title={title}
    style={{
      ...gradeChipStyle(grade),
      border: '1px solid',
      minWidth: size === 'm' ? 30 : 26,
      height: size === 'm' ? 30 : 26,
      borderRadius: size === 'm' ? 9 : 7,
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size === 'm' ? 14 : 13, fontWeight: 700, flexShrink: 0,
    }}
  >
    {grade}
  </span>
);

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
