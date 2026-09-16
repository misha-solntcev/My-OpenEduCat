/**
 * Таймлайн учебного дня на главной (этап 2 редизайна, мокап
 * design/stitch-main-timeline.html).
 *
 * Рельса: кружок-номер 24px + линия-соединитель. Акцент состояния дня —
 * элемент рельсы, «ползёт» вместе со временем (состояние считает клиент):
 *   before  — шапка рельсы («Уроки начнутся через N минут»);
 *   lesson  — на месте текущего слота (live-card с прогрессом урока);
 *   break   — между слотами («Перемена» + осталось);
 *   after   — футер рельсы («Все уроки завершены»).
 * Акцент всегда синий (утверждено: не зелёный даже на «завершены»).
 *
 * Стили: VKUI токены + инлайн, кастомных css-классов нет.
 */
import React from 'react';
import { Text, Caption, Avatar } from '@vkontakte/vkui';
import {
  Icon16MoreHorizontal,
  Icon16CheckCircleOutline,
} from '@vkontakte/icons';
import { useSchoolNowMinutes } from '@/shared/hooks/useSchoolNow';
import { initialsOf } from '@/shared/lib/initials';
import {
  RailNum,
  RailLine,
  LiveCard,
  AccentProgress,
  accentSlotStyle,
  firstNamePatronymic,
  timingToMinutes,
} from '@/shared/components/timelinePrimitives';
import type { FeedLesson } from '@/shared/lib/types';

type DayPhase = 'before' | 'lesson' | 'break' | 'after';

interface DayState {
  phase: DayPhase;
  /** Индекс слота: текущего (lesson) или следующего (break). */
  slotIndex: number;
  /** Процент прошлого этапа прогресса (0..100). */
  progress: number;
  /** Минут до начала ближайшего события (перемена/до уроков). */
  minutesLeft: number;
  /** Длина перемены в минутах. */
  breakTotal: number;
}

/** Состояние дня из слотов. Пустой день — null (рендерим заглушку). */
const computeDayState = (lessons: FeedLesson[], nowMin: number): DayState | null => {
  const slots = lessons
    .map(l => ({ l, range: timingToMinutes(l.timing) }))
    .filter((s): s is { l: FeedLesson; range: [number, number] } => s.range != null);
  if (!slots.length) return null;

  for (let i = 0; i < slots.length; i++) {
    const [start, end] = slots[i].range;
    if (nowMin < start) {
      // До первого урока или перемена перед слотом i.
      if (i === 0) {
        return {
          phase: 'before', slotIndex: 0, progress: 0,
          minutesLeft: start - nowMin, breakTotal: 0,
        };
      }
      const prevEnd = slots[i - 1].range[1];
      const total = start - prevEnd;
      return {
        phase: 'break', slotIndex: i, progress: 0,
        minutesLeft: start - nowMin, breakTotal: total,
      };
    }
    if (nowMin < end) {
      const progress = Math.round(((nowMin - start) / (end - start)) * 100);
      return { phase: 'lesson', slotIndex: i, progress, minutesLeft: 0, breakTotal: 0 };
    }
  }
  return { phase: 'after', slotIndex: slots.length - 1, progress: 100, minutesLeft: 0, breakTotal: 0 };
};

// --- Строка слота таймлайна --------------------------------------------------

const TimelineSlot: React.FC<{
  num: number;
  lesson: FeedLesson;
  status: 'past' | 'now' | 'future';
  /** Процент урока — рисуется только в акцентном слоте. */
  progress?: number;
  showBatch?: boolean;
  onOpenJournal?: (sheetId: number) => void;
  /** Последний слот дня: рельсу вниз не тянем (соединять нечего). */
  isLast?: boolean;
}> = ({ num, lesson, status, progress, showBatch, onOpenJournal, isLast }) => {
  const clickable = Boolean(onOpenJournal && lesson.sheet_id);
  const isNow = status === 'now';
  const accent = isNow ? accentSlotStyle : undefined;
  // Цвет второстепенных надписей: прошедшие — приглушённые, текущие и
  // будущие — ярче (пожелание Миши 2026-09-15), в акценте — белый.
  const subColor = isNow
    ? 'var(--vkui--color_text_contrast)'
    : status === 'past'
      ? 'var(--vkui--color_text_secondary)'
      : 'var(--vkui--color_text_primary)';
  return (
    <div style={{ padding: 10, paddingTop: isNow ? 12 : 10, marginBottom: isLast ? undefined : -20 }}>
      <div style={{ display: 'flex', gap: 10 }}>
        <div style={{ width: 24, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', overflow: 'visible' }}>
          <RailNum tone={isNow ? 'accent' : status === 'past' ? 'past' : 'default'}>{num}</RailNum>
          {!isLast && <RailLine dimmed={status === 'past'} />}
        </div>
        <div
          style={{
            flex: 1, minWidth: 0,
            opacity: status === 'past' ? 0.55 : 1,
            cursor: clickable ? 'pointer' : undefined,
            ...(accent || {}),
          }}
          onClick={clickable ? () => onOpenJournal!(lesson.sheet_id!) : undefined}
        >
          {/* Строка 1: предмет + время справа */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
            <Text weight="2" style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {lesson.subject}{showBatch && lesson.batch ? ` · ${lesson.batch}` : ''}
            </Text>
            <Caption style={{ color: subColor, flexShrink: 0 }}>
              {lesson.timing}
            </Caption>
          </div>
          {/* Строка 2: аватар + учитель + кабинет справа */}
          {(lesson.faculty || lesson.room) && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                <Avatar
                  size={24}
                  src={lesson.faculty_avatar || undefined}
                  fallbackIcon={
                    <span style={{ fontSize: 10, fontWeight: 600 }}>
                      {initialsOf(lesson.faculty)}
                    </span>
                  }
                  objectPosition="center top"
                  style={{ flexShrink: 0, borderRadius: 4 }}
                />
                <Caption style={{
                  color: subColor, minWidth: 0,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {lesson.faculty ? firstNamePatronymic(lesson.faculty) : ''}
                </Caption>
              </div>
              {lesson.room && (
                <Caption style={{ color: subColor, flexShrink: 0 }}>
                  Каб. {lesson.room}
                </Caption>
              )}
            </div>
          )}
          {isNow && progress != null && <AccentProgress progress={progress} />}
        </div>
      </div>
    </div>
  );
};

// --- Таймлайн дня ------------------------------------------------------------

export const TodayTimeline: React.FC<{
  lessons: FeedLesson[];
  showBatch?: boolean;
  onOpenJournal?: (sheetId: number) => void;
}> = ({ lessons, showBatch, onOpenJournal }) => {
  // Тик 30 с: статус слота и прогресс «ползут» без перезагрузки ленты.
  const nowMin = useSchoolNowMinutes();
  const state = computeDayState(lessons, nowMin);

  if (!state) return null;
  const { phase, slotIndex, progress, minutesLeft } = state;

  /** Акцент-карточка по фазе (тексты — по утверждённому мокапу). */
  const liveCard = (() => {
    if (phase === 'before') {
      const m = minutesLeft;
      return (
        <LiveCard
          text={m >= 60
            ? `Уроки начнутся через ${Math.floor(m / 60)} ч ${m % 60} мин`
            : `Уроки начнутся через ${m} мин`}
        />
      );
    }
    if (phase === 'break') {
      // Большой перерыв (≥30 мин) — обед (утверждено Мишей 2026-09-15).
      const isLunch = state.breakTotal >= 30;
      return (
        <LiveCard
          text={isLunch ? 'Обед' : 'Перемена'}
          after={`${minutesLeft} минут`}
          progress={state.breakTotal > 0
            ? ((state.breakTotal - minutesLeft) / state.breakTotal) * 100
            : undefined}
        />
      );
    }
    if (phase === 'lesson') {
      // Слот вокруг карточки уже показывает предмет, время, кабинет и
      // учителя, а остаток времени виден по полосе прогресса — не дублируем.
      return (
        <LiveCard
          text="Идёт сейчас"
          progress={progress}
        />
      );
    }
    // after
    return <LiveCard text="Все уроки завершены" />;
  })();

  /** Иконка в кружке акцента: dots на перемене, check после. У шапки
   *  «до уроков» иконки нет (утверждено 2026-09-15 — лишняя). */
  const capIcon = phase === 'break'
    ? <Icon16MoreHorizontal width={12} height={12} fill="currentColor" />
    : phase === 'after'
      ? <Icon16CheckCircleOutline width={14} height={14} fill="currentColor" />
      : null;

  const items: React.ReactNode[] = [];

  // Акцент в шапке рельсы (до уроков).
  if (phase === 'before') {
    items.push(
      <div key="cap" style={{ padding: 10, paddingBottom: 0, display: 'flex', gap: 10 }}>
        <div style={{ width: 24, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <RailNum tone="accent">{capIcon}</RailNum>
        </div>
        <div style={{ flex: 1, paddingTop: 0 }}>
          {liveCard}
        </div>
      </div>,
    );
  }

  lessons.forEach((l, i) => {
    const range = timingToMinutes(l.timing);
    const status: 'past' | 'now' | 'future' = !range
      ? 'future'
      : nowMin >= range[1]
        ? 'past'
        : nowMin >= range[0] ? 'now' : 'future';

    items.push(
      <TimelineSlot
        key={l.id}
        num={i + 1}
        lesson={l}
        status={status}
        isLast={i === lessons.length - 1}
        // Слот текущего урока красится синим целиком, прогресс в хвосте.
        progress={phase === 'lesson' && i === slotIndex ? progress : undefined}
        showBatch={showBatch}
        onOpenJournal={onOpenJournal}
      />,
    );

    // Перемена после слота i, если акцент именно здесь.
    if (phase === 'break' && i === slotIndex - 1) {
      items.push(
        <div key={`break-${i}`} style={{ padding: 10, paddingTop: 0, paddingBottom: 10, display: 'flex', gap: 10 }}>
          <div style={{ width: 24, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <RailNum tone="accent">{capIcon}</RailNum>
            {i < lessons.length - 1 && <RailLine />}
          </div>
          <div style={{ flex: 1 }}>
            {liveCard}
          </div>
        </div>,
      );
    }
  });

  // Акцент в футере рельсы (уроки завершены).
  if (phase === 'after') {
    items.push(
      <div key="end" style={{ padding: 10, paddingTop: 0, display: 'flex', gap: 10 }}>
        <div style={{ width: 24, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <RailNum tone="accent">{capIcon}</RailNum>
        </div>
        <div style={{ flex: 1 }}>
          {liveCard}
        </div>
      </div>,
    );
  }

  return <div>{items}</div>;
};
