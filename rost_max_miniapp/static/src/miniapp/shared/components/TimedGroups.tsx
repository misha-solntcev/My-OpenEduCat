/**
 * Группировка уроков по таймингу (слотам «09:30 - 10:15») — для админа,
 * у которого в расписании вся школа. Каждый слот = аккордеон, раскрыт
 * слот, в котором сейчас идёт урок (только для сегодняшней даты).
 * Используется на странице расписания и в ленте дня на главной.
 */
import React from 'react';
import { Accordion, Badge, Caption, Text } from '@vkontakte/vkui';
import { LessonRow, lessonStatus, startTimeOf, type ChipTone, type LessonRowData } from '@/shared/components/LessonRow';
import { schoolNowMinutes } from '@/shared/lib/date';

/** Группировка по таймингу (сохраняя порядок прихода с сервера). */
export const groupByTiming = <T extends { timing: string }>(lessons: T[]): { timing: string; lessons: T[] }[] => {
  const groups: { timing: string; lessons: T[] }[] = [];
  const index = new Map<string, { timing: string; lessons: T[] }>();
  for (const l of lessons) {
    const key = l.timing || '';
    let g = index.get(key);
    if (!g) {
      g = { timing: key, lessons: [] };
      index.set(key, g);
      groups.push(g);
    }
    g.lessons.push(l);
  }
  return groups;
};

const pluralRu = (n: number): string => {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return 'урок';
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'урока';
  return 'уроков';
};

export const TimedGroups: React.FC<{
  lessons: (LessonRowData & Record<string, unknown>)[];
  isToday: boolean;
  /** Прокидывается в LessonRow каждой строки слота. */
  rowProps?: (lesson: never) => Record<string, unknown>;
  onOpenLesson?: (sheetId: number) => void;
  /** Ключ для reset'а раскрытия при смене дня/фильтров. */
  resetKey?: string;
}> = ({ lessons, isToday, onOpenLesson, resetKey }) => {
  // Дефолт раскрытия: слот «сейчас», а в его отсутствие (перемена, обед,
  // до первого урока) — ближайший будущий; когда все прошли — последний.
  // Бейдж объясняет, почему слот раскрыт, когда урока «сейчас» нет.
  const groups = groupByTiming(lessons);
  let defaultTiming = '';
  let badge: { tone: ChipTone; label: string } | null = null;
  if (isToday && groups.length) {
    // Начало слота в минутах («09:30 - 10:15» -> 570).
    const starts = (timing: string): number => {
      const [h, m] = startTimeOf(timing).split(':').map(Number);
      return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : -1;
    };
    const nowMin = schoolNowMinutes();
    const nowIdx = groups.findIndex(g =>
      g.lessons.some(l => lessonStatus(l.timing, isToday) === 'now'));
    const nextIdx = nowIdx >= 0 ? nowIdx : groups.findIndex(g => starts(g.timing) > nowMin);
    const idx = nowIdx >= 0 ? nowIdx : (nextIdx >= 0 ? nextIdx : groups.length - 1);
    defaultTiming = groups[idx].timing;
    if (nowIdx >= 0) {
      badge = { tone: 'blue', label: 'Идёт сейчас' };
    } else if (nextIdx >= 0) {
      // Перерыв/обед: зазор от конца предыдущего слота до начала выбранного.
      // Большой зазор (>= 60 мин) считаем обедом; до первого урока — тоже
      // «Перемена» (отдельного состояния не заводим).
      const prev = groups[idx - 1];
      const prevEnd = prev
        ? (prev.timing.split(' - ')[1] || '').trim()
        : '';
      const [eh, em] = prevEnd.split(':').map(Number);
      const gapMin = Number.isFinite(eh) && Number.isFinite(em)
        ? starts(groups[idx].timing) - (eh * 60 + em)
        : 0;
      badge = gapMin >= 60
        ? { tone: 'blue', label: 'Обед' }
        : { tone: 'blue', label: 'Перемена' };
    }
  }
  return (
    <>
      {groups.map(g => (
        <TimedGroup
          key={g.timing}
          timing={g.timing}
          lessons={g.lessons}
          isToday={isToday}
          defaultExpanded={isToday && g.timing === defaultTiming}
          badge={g.timing === defaultTiming ? badge : null}
          onOpenLesson={onOpenLesson}
          resetKey={resetKey}
        />
      ))}
    </>
  );
};

const TimedGroup: React.FC<{
  timing: string;
  lessons: (LessonRowData & Record<string, unknown>)[];
  isToday: boolean;
  defaultExpanded: boolean;
  /** Пилюля в заголовке («Идёт сейчас», «Перемена», «Обед»). */
  badge: { tone: ChipTone; label: string } | null;
  onOpenLesson?: (sheetId: number) => void;
  resetKey?: string;
}> = ({ timing, lessons, isToday, defaultExpanded, badge, onOpenLesson, resetKey }) => {
  const status = lessons.map(l => lessonStatus(l.timing, isToday));
  const hasNow = status.includes('now');
  const hasPast = status.every(s => s === 'past');
  const [expanded, setExpanded] = React.useState(defaultExpanded);

  // Переход на другой день / смена фильтров: перечитываем дефолт
  // (раскрыт «сейчас» или ближайший слот); пользовательский выбор
  // живёт до этого.
  React.useEffect(
    () => { setExpanded(defaultExpanded); },
    [defaultExpanded, timing, lessons.length, resetKey]);

  const stateColor = hasNow
    ? 'var(--vkui--color_text_accent)'
    : hasPast
      ? 'var(--vkui--color_text_secondary)'
      : 'var(--vkui--color_text_primary)';

  return (
    <Accordion expanded={expanded} onChange={setExpanded} id={`slot-${timing}`}>
      <Accordion.Summary
        after={
          <>
            {badge && <Badge mode="prominent">{badge.label}</Badge>}
            <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
              {lessons.length} {pluralRu(lessons.length)}
            </Caption>
          </>
        }
      >
        <Text weight="2" style={{ color: stateColor }}>
          {startTimeOf(timing)}
        </Text>
      </Accordion.Summary>
      <Accordion.Content>
        {lessons.map((l, i) => (
          <LessonRow
            key={l.id}
            lesson={l}
            status={status[i]}
            showBatch
            showFaculty
            onClick={onOpenLesson && l.sheet_id ? () => onOpenLesson(l.sheet_id!) : undefined}
          />
        ))}
      </Accordion.Content>
    </Accordion>
  );
};
