/**
 * Общая строка урока: аватар учителя + время + предмет + класс + чипы статуса.
 * Используется на странице расписания и в ленте дня на главной.
 *
 * Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов
 * (чипы — инлайн-стили, как .chip.red/.chip.blue из макета
 * design/dashboard-teacher-admin.html).
 */
import React from 'react';
import { Avatar, SimpleCell, Text, Counter } from '@vkontakte/vkui';
import { initialsOf } from '@/shared/lib/initials';
import { schoolNowMinutes } from '@/shared/lib/date';

/** «5А 2026/2027» -> «5А»: учебный год в имени класса не нужен. */
const BATCH_YEAR_RE = /\s*\d{4}[/\-–]\d{4}\s*/;
export const shortBatchName = (name: string): string =>
  name.replace(BATCH_YEAR_RE, ' ').trim();

/** Время начала урока из «09:30 - 10:15». */
export const startTimeOf = (timing: string): string =>
  (timing || '').split(' - ')[0] || timing;

/** «09:30 - 10:15» -> ['09:30', '10:15'] */
const splitHM = (timing: string): [string, string] | null => {
  const parts = (timing || '').split(' - ');
  if (parts.length < 2) return null;
  const parse = (s: string) => s.trim().match(/^(\d{1,2}):(\d{2})$/);
  const a = parse(parts[0]);
  const b = parse(parts[1]);
  if (!a || !b) return null;
  return [`${a[1]}:${a[2]}`, `${b[1]}:${b[2]}`];
};

export type LessonStatus = 'past' | 'now' | 'future';

/**
 * Статус урока относительно текущего момента. Красим ТОЛЬКО при просмотре
 * сегодняшней даты (isToday): прошлые/будущие дни нейтральны (весь день
 * в прошлом/будущем). Время — школьная зона (Europe/Moscow), тайминг
 * из Odoo тоже в ней: миниапп открывают из других часовых поясов.
 */
export const lessonStatus = (
  timing: string,
  isToday: boolean,
): LessonStatus | null => {
  if (!isToday || !timing) return null;
  const hm = splitHM(timing);
  if (!hm) return null;
  const toMin = (s: string) => {
    const [h, m] = s.split(':').map(Number);
    return h * 60 + m;
  };
  const minutes = schoolNowMinutes();
  if (minutes < toMin(hm[0])) return 'future';
  if (minutes >= toMin(hm[1])) return 'past';
  return 'now';
};

/** Фон строки по статусу: past — серый, now — акцентная подложка. */
export const STATUS_BACKGROUND: Record<LessonStatus | 'none', string | undefined> = {
  past: 'var(--vkui--color_background_secondary)',
  now: 'var(--vkui--color_background_accent_tinted)',
  future: undefined,
  none: undefined,
};

// --- Чипы статуса (пилюли как тэги в Odoo) ---------------------------------

const chipBase: React.CSSProperties = {
  display: 'inline-block',
  fontSize: 11,
  fontWeight: 600,
  lineHeight: '16px',
  padding: '1px 8px',
  borderRadius: 99,
};

/** Цветовые схемы чипов: фон/текст на VKUI-токенах (адаптивны к теме). */
const CHIP_TONES = {
  red: {
    background: 'var(--vkui--color_background_negative_tinted)',
    color: 'var(--vkui--color_text_negative)',
  },
  blue: {
    background: 'var(--vkui--color_background_accent_tinted)',
    color: 'var(--vkui--color_text_accent)',
  },
  green: {
    background: 'var(--vkui--color_background_positive_tinted)',
    color: 'var(--vkui--color_text_positive)',
  },
} as const;

export type ChipTone = keyof typeof CHIP_TONES;

/** Пилюля статуса («Журнал не заполнен», «Есть ДЗ») — как тэг в Odoo. */
export const StatusChip: React.FC<{ tone: ChipTone; children: React.ReactNode }> = ({
  tone,
  children,
}) => <span style={{ ...chipBase, ...CHIP_TONES[tone] }}>{children}</span>;

// --- Строка урока -----------------------------------------------------------

export interface LessonRowData {
  id: number;
  subject: string;
  batch: string;
  faculty: string;
  timing: string;
  /** URL аватара учителя (/web/image). Пусто — нет фото или гость. */
  faculty_avatar?: string;
  /** id op.attendance.sheet (журнал). Есть только у teacher/admin. */
  sheet_id?: number | null;
}

export interface LessonRowProps {
  lesson: LessonRowData;
  /** Статус для подсветки фона (считает вызывающий — он знает дату). */
  status?: LessonStatus | null;
  /** Класс в Counter справа (учитель/админ в ленте дня). */
  showBatch?: boolean;
  /** ФИО учителя в подписи (расписание). */
  showFaculty?: boolean;
  /** Чип «Журнал не заполнен» (учитель/админ, лента дня). */
  journalUnfilled?: boolean;
  /** Чип «Есть ДЗ» при наличии текста ДЗ. */
  hasHomework?: boolean;
  /** Плашка «Сейчас» справа (лента дня). */
  isNow?: boolean;
  onClick?: () => void;
}

export const LessonRow: React.FC<LessonRowProps> = ({
  lesson,
  status,
  showBatch,
  showFaculty,
  journalUnfilled,
  hasHomework,
  isNow,
  onClick,
}) => {
  const chips: React.ReactNode[] = [];
  if (showFaculty && lesson.faculty) {
    chips.push(<span key="faculty">{lesson.faculty}</span>);
  }
  if (journalUnfilled) {
    chips.push(<StatusChip key="unfilled" tone="red">Журнал не заполнен</StatusChip>);
  }
  if (hasHomework) {
    chips.push(<StatusChip key="hw" tone="blue">Есть ДЗ</StatusChip>);
  }

  return (
    <SimpleCell
      onClick={onClick}
      style={{ backgroundColor: STATUS_BACKGROUND[status ?? 'none'] }}
      before={
        <Avatar
          size={40}
          src={lesson.faculty_avatar || undefined}
          fallbackIcon={
            <span style={{ fontSize: 16, fontWeight: 600 }}>
              {initialsOf(lesson.faculty)}
            </span>
          }
          objectPosition="center top"
          style={{ borderRadius: 8, flexShrink: 0 }}
        />
      }
      after={
        <>
          {isNow && <StatusChip tone="green">Сейчас</StatusChip>}
          {showBatch && lesson.batch && (
            <Counter
              mode="tertiary"
              size="s"
              style={{ flexShrink: 0, fontSize: 15, fontWeight: 500 }}
            >
              {shortBatchName(lesson.batch)}
            </Counter>
          )}
        </>
      }
      subtitle={
        chips.length ? (
          <span style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {chips}
          </span>
        ) : undefined
      }
    >
      <Text
        weight="2"
        inline
        style={{
          marginRight: 6,
          color: 'var(--vkui--color_text_accent)',
        }}
      >
        {startTimeOf(lesson.timing)}
      </Text>
      {lesson.subject}
    </SimpleCell>
  );
};
