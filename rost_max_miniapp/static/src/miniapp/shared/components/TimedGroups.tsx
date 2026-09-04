/**
 * Группировка уроков по таймингу (слотам «09:30 - 10:15») — для админа,
 * у которого в расписании вся школа. Каждый слот = аккордеон, раскрыт
 * слот, в котором сейчас идёт урок (только для сегодняшней даты).
 * Используется на странице расписания и в ленте дня на главной.
 */
import React from 'react';
import { Accordion, Caption, Text } from '@vkontakte/vkui';
import { LessonRow, lessonStatus, startTimeOf, type LessonRowData } from '@/shared/components/LessonRow';

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
}> = ({ lessons, isToday, onOpenLesson, resetKey }) => (
  <>
    {groupByTiming(lessons).map(g => (
      <TimedGroup
        key={g.timing}
        timing={g.timing}
        lessons={g.lessons}
        isToday={isToday}
        onOpenLesson={onOpenLesson}
        resetKey={resetKey}
      />
    ))}
  </>
);

const TimedGroup: React.FC<{
  timing: string;
  lessons: (LessonRowData & Record<string, unknown>)[];
  isToday: boolean;
  onOpenLesson?: (sheetId: number) => void;
  resetKey?: string;
}> = ({ timing, lessons, isToday, onOpenLesson, resetKey }) => {
  const status = lessons.map(l => lessonStatus(l.timing, isToday));
  const hasNow = status.includes('now');
  const hasPast = status.every(s => s === 'past');
  const [expanded, setExpanded] = React.useState(hasNow);

  // Переход на другой день / смена фильтров: перечитываем дефолт
  // (раскрыт только «сейчас»); пользовательский выбор живёт до этого.
  React.useEffect(() => { setExpanded(hasNow); }, [hasNow, timing, lessons.length, resetKey]);

  const stateColor = hasNow
    ? 'var(--vkui--color_text_accent)'
    : hasPast
      ? 'var(--vkui--color_text_secondary)'
      : 'var(--vkui--color_text_primary)';

  return (
    <Accordion expanded={expanded} onChange={setExpanded} id={`slot-${timing}`}>
      <Accordion.Summary
        after={
          <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
            {lessons.length} {pluralRu(lessons.length)}
          </Caption>
        }
      >
        <Text weight="2" style={{ color: stateColor }}>
          {startTimeOf(timing)}
        </Text>
        {hasNow ? ' · Идёт сейчас' : ''}
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
