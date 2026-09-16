import React from 'react';
import { Panel, Flex, Text, Spinner, Box, Placeholder, IconButton, CustomSelect, ModalPage, ModalPageHeader, PanelHeaderButton, Avatar } from '@vkontakte/vkui';
import {
  Icon24ChevronLeftOutline,
  Icon24ChevronRightOutline,
  Icon56CalendarOutline,
  Icon24CalendarOutline,
  Icon24Dismiss,
} from '@vkontakte/icons';
import { Calendar } from '@vkontakte/vkui';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { TimedGroups } from '@/shared/components/TimedGroups';
import { useSchoolNowMinutes } from '@/shared/hooks/useSchoolNow';
import { initialsOf } from '@/shared/lib/initials';
import {
  RailNum,
  RailLine,
  slotCardStyle,
  AccentProgress,
  accentSlotStyle,
  firstNamePatronymic,
  timingToMinutes,
} from '@/shared/components/timelinePrimitives';
import { toISO, today, schoolTodayISO, startOfWeek, SHORT_WEEKDAYS } from '@/shared/lib/date';
import type { Lesson, Faculty, Batch, TimetableResponse, FacultiesResponse, BatchesResponse } from '@/shared/lib/types';

interface TimetablePageProps {
  id: string;
  onOpenLesson: (id: number) => void;
}

type SelectOption = { value: string; label: string };

/** Лента дат пн–вс недели выбранной даты + навигация по неделям */
const DayStrip: React.FC<{ selected: string; onSelect: (iso: string) => void }> = ({ selected, onSelect }) => {
  const selDate = new Date(selected + 'T00:00:00');
  const monday = startOfWeek(selDate || new Date());
  const todayISO = schoolTodayISO();

  return (
    <Box paddingBlockEnd="m">
      <Flex gap={2} justify="center">
        {Array.from({ length: 7 }, (_, i) => {
          const d = new Date(monday);
          d.setDate(monday.getDate() + i);
          const iso = toISO(d);
          const isSel = iso === selected;
          const isToday = iso === todayISO;
          return (
            <Flex
              key={iso}
              direction="column"
              align="center"
              justify="center"
              style={{
                minWidth: 44,
                height: 56,
                borderRadius: 12,
                cursor: 'pointer',
                background: isSel ? 'var(--vkui--color_background_accent)' : 'transparent',
                flexShrink: 0,
              }}
              onClick={() => onSelect(iso)}
            >
              <Text
                weight={isSel ? '2' : '1'}
                style={{
                  fontSize: 11,
                  color: isSel
                    ? 'var(--vkui--color_text_contrast)'
                    : 'var(--vkui--color_text_secondary)',
                }}
              >
                {SHORT_WEEKDAYS[i]}
              </Text>
              <Text
                weight={isSel || isToday ? '2' : '3'}
                style={{
                  fontSize: 16,
                  color: isSel
                    ? 'var(--vkui--color_text_contrast)'
                    : 'var(--vkui--color_text_primary)',
                }}
              >
                {d.getDate()}
              </Text>
            </Flex>
          );
        })}
      </Flex>
    </Box>
  );
};

// --- Таймлайн расписания -----------------------------------------------------

type SlotStatus = 'past' | 'now' | 'future';

/** Строка урока в рельсе расписания (мокап: время, предмет, мета, чипы).
 *  isLast — последний слот дня: рельса не тянется вниз (соединять нечего). */
const TimetableSlot: React.FC<{
  num: number;
  lesson: Lesson;
  status: SlotStatus;
  isLast: boolean;
  /** Процент урока — только в акцентном (текущем) слоте. */
  nowProgress?: number;
  showBatch: boolean;
  showFaculty: boolean;
  onOpenLesson?: (id: number) => void;
}> = ({ num, lesson, status, isLast, nowProgress, showBatch, showFaculty, onOpenLesson }) => {
  // Журнал: только там, где есть sheet_id (teacher/admin).
  const clickable = Boolean(onOpenLesson && lesson.sheet_id);

  // Цвет второстепенных надписей: прошедшие — приглушённые, текущие и
  // будущие — ярче (пожелание Миши 2026-09-15), в акценте — белый.
  const subColor = status === 'now'
    ? 'var(--vkui--color_text_contrast)'
    : status === 'past'
      ? 'var(--vkui--color_text_secondary)'
      : 'var(--vkui--color_text_primary)';

  // Каждый урок — своя карточка (просьба Миши 2026-09-15): фон content,
  // тень, внутренний паддинг. Рельса (кружок+линия) слева ВНЕ карточки,
  // вертикальный центр строки. Между строками честный зазор 10px
  // (lineGap), карточки не налезают друг на друга; линию через зазор
  // дотягивает RailLine bridge, а не отрицательный margin строки.
  return (
    <div style={{
      display: 'flex', gap: 10, padding: '5px 16px',
      zIndex: 2,
    }}>
      <div style={{ width: 24, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 9 }}>
        <RailNum tone={status === 'now' ? 'accent' : status === 'past' ? 'past' : 'default'}>{num}</RailNum>
        {!isLast && <RailLine dimmed={status === 'past'} bridge={24} />}
      </div>
      <div
        style={{
          flex: 1, minWidth: 0, padding: '10px 12px',
          ...slotCardStyle,
          opacity: status === 'past' ? 0.55 : 1,
          cursor: clickable ? 'pointer' : undefined,
          ...(status === 'now' ? accentSlotStyle : {}),
        }}
          onClick={clickable ? () => onOpenLesson!(lesson.sheet_id!) : undefined}
        >
          {/* Строка 1: предмет + время справа */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
            <Text weight="2" style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {lesson.subject}{showBatch && lesson.batch ? ` · ${lesson.batch}` : ''}
            </Text>
            <Text weight="1" style={{
              flexShrink: 0, fontSize: 13,
              color: subColor,
              opacity: status === 'now' ? 0.8 : 1,
            }}>
              {lesson.timing}
            </Text>
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
                <Text weight="1" style={{
                  minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13,
                  color: subColor,
                  opacity: status === 'now' ? 0.8 : 1,
                }}>
                  {showFaculty && lesson.faculty ? firstNamePatronymic(lesson.faculty) : ''}
                </Text>
              </div>
              {lesson.room && (
                <Text weight="1" style={{
                  flexShrink: 0, fontSize: 13,
                  color: subColor,
                  opacity: status === 'now' ? 0.8 : 1,
                }}>
                  Каб. {lesson.room}
                </Text>
              )}
            </div>
          )}
          {status === 'now' && nowProgress != null && <AccentProgress progress={nowProgress} />}
      </div>
    </div>
  );
};

/** Таймлайн дня расписания: как на главной, но без акцентов-состояний
 *  для прошлых/будущих дат; на сегодня — live-card текущего слота. */
const TimetableTimeline: React.FC<{
  lessons: Lesson[];
  isToday: boolean;
  showBatch: boolean;
  onOpenLesson?: (id: number) => void;
}> = ({ lessons, isToday, showBatch, onOpenLesson }) => {
  const nowMin = useSchoolNowMinutes();

  // Текущий слот только на сегодняшней дате.
  let nowIndex = -1;
  if (isToday) {
    lessons.forEach((l, i) => {
      const range = timingToMinutes(l.timing);
      if (range && nowMin >= range[0] && nowMin < range[1]) {
        nowIndex = i;
      }
    });
  }

  const items: React.ReactNode[] = [];
  lessons.forEach((l, i) => {
    const range = timingToMinutes(l.timing);
    // Не-сегодняшняя дата: весь день нейтрален (future), без past/now.
    const status: SlotStatus = !isToday || !range
      ? 'future'
      : nowMin >= range[1] ? 'past' : nowMin >= range[0] ? 'now' : 'future';

    items.push(
      <TimetableSlot
        key={l.id}
        num={i + 1}
        lesson={l}
        status={status}
        isLast={i === lessons.length - 1}
        // Слот текущего урока красится синим целиком, прогресс в хвосте.
        nowProgress={i === nowIndex && range
          ? ((nowMin - range[0]) / (range[1] - range[0])) * 100
          : undefined}
        showBatch={showBatch}
        showFaculty
        onOpenLesson={onOpenLesson}
      />,
    );
  });

  return <div>{items}</div>;
};

export const TimetablePage: React.FC<TimetablePageProps> = ({ id, onOpenLesson }) => {
  // Дата и фильтры — локальный стейт экрана: всегда стартуем с «сегодня»
  // (Europe/Moscow) и без фильтров. Эпик держит View смонтированным,
  // поэтому выбор переживает переключение вкладок, но не перезапуск.
  const [globalDate, setGlobalDate] = React.useState(today);
  const [selectedFaculty, setSelectedFaculty] = React.useState<number | null>(null);
  const [selectedBatch, setSelectedBatch] = React.useState<number | null>(null);
  const addToast = useToast();

  const [lessons, setLessons] = React.useState<Lesson[]>([]);
  const [faculties, setFaculties] = React.useState<Faculty[]>([]);
  const [batches, setBatches] = React.useState<Batch[]>([]);
  const [isAdmin, setIsAdmin] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [calendarOpen, setCalendarOpen] = React.useState(false);

  React.useEffect(() => {
    // Оба справочника отдаются только админу (для остальных — пустые
    // списки, см. роуты) — заодно служат детекцией роли.
    Promise.all([
      apiGet<FacultiesResponse>('/rost_max/api/faculties'),
      apiGet<BatchesResponse>('/rost_max/api/batches'),
    ])
      .then(([facData, batchData]) => {
        if (facData.faculties?.length) {
          setFaculties(facData.faculties);
          setIsAdmin(true);
        }
        if (batchData.batches?.length) {
          setBatches(batchData.batches);
        }
      })
      .catch((err: unknown) => {
        console.error('Failed to load filter dictionaries:', err);
      });
  }, []);

  const loadLessons = React.useCallback(async () => {
    setLoading(true);
    try {
      let url = `/rost_max/api/timetable?date=${globalDate}`;
      if (selectedFaculty) url += `&faculty_id=${selectedFaculty}`;
      if (selectedBatch) url += `&batch_id=${selectedBatch}`;
      const data = await apiGet<TimetableResponse>(url);
      setLessons(data.lessons || []);
    } catch {
      setLessons([]);
      addToast('Не удалось загрузить расписание', 'error');
    } finally {
      setLoading(false);
    }
  }, [globalDate, selectedFaculty, selectedBatch, addToast]);

  React.useEffect(() => { loadLessons(); }, [loadLessons]);

  const isToday = globalDate === schoolTodayISO();

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
  };

  const facultyOptions: SelectOption[] = [
    { value: '', label: 'Все учителя' },
    ...faculties.map(f => ({ value: String(f.id), label: f.name })),
  ];

  const batchOptions: SelectOption[] = [
    { value: '', label: 'Все классы' },
    // Натуральная сортировка: «1А, 2А, ... 10А, 11А», а не «1, 10, 11, 2».
    // sequence у всех классов одинаковый (дефолт), серверный order не спасает.
    ...batches
      .slice()
      .sort((a, b) =>
        a.name.localeCompare(b.name, 'ru', { numeric: true })
      )
      .map(b => ({ value: String(b.id), label: b.name })),
  ];

  // Переключение недели относительно текущей выбранной даты
  const shiftWeek = (days: number) => {
    const d = new Date(globalDate + 'T00:00:00');
    d.setDate(d.getDate() + days);
    setGlobalDate(toISO(d));
  };

  const goToday = () => setGlobalDate(schoolTodayISO());

  return (
    <Panel id={id}>
      {/* Корневой таб: без PanelHeader — активный таб и так подсвечен в
          таббаре. Кнопка фильтра (админ) переехала в ленту дат. */}
      <Box padding="m" paddingInline="none">
        {/* Лента дат пн-вс + переключение недель. Стрелки — крупные
            тапабельные зоны (44px) со своим отступом от края экрана. */}
        <Flex align="center" justify="space-between">
          <IconButton
            label="Предыдущая неделя"
            style={{ width: 44, height: 44, marginLeft: 4, flexShrink: 0 }}
            onClick={() => shiftWeek(-7)}
          >
            <Icon24ChevronLeftOutline />
          </IconButton>
          <Flex align="center" gap={2}>
            <Text weight="2">{formatDate(globalDate)}</Text>
            <IconButton
              label="Выбрать дату"
              onClick={() => setCalendarOpen(true)}
            >
              <Icon24CalendarOutline />
            </IconButton>
            <Text
              weight="1"
              style={{ cursor: 'pointer', color: 'var(--vkui--color_text_accent)' }}
              onClick={goToday}
            >
              Сегодня
            </Text>
          </Flex>
          <IconButton
            label="Следующая неделя"
            style={{ width: 44, height: 44, marginRight: 4, flexShrink: 0 }}
            onClick={() => shiftWeek(7)}
          >
            <Icon24ChevronRightOutline />
          </IconButton>
        </Flex>

        <DayStrip selected={globalDate} onSelect={setGlobalDate} />

        {/* Фильтры — только админ, показываются всегда (без кнопки-тумблера).
            ВАЖНО: у VKUI Flex по умолчанию flex-wrap — без noWrap селекты
            уходят друг под друга. flexBasis:0 + flexGrow:1 делят строку
            поровну. Дропдаун раскрывается на всю ширину своего поля
            (floating-ui sameWidth, dropdownAutoWidth=false по умолчанию).
            Белый фон + рамка, чтобы не сливались с серым фоном панели. */}
        {isAdmin && (
          <Flex
            gap={8}
            noWrap
            style={{
              // Отступы как у карточки уроков ниже (Box paddingInline="s"),
              // снизу минимальный зазор до списка.
              paddingInline: 'var(--vkui--spacing_size_s)',
              paddingBlockEnd: 'var(--vkui--spacing_size_xs)',
            }}
          >
            <CustomSelect
              style={{
                flexGrow: 1,
                flexBasis: 0,
                minWidth: 0,
                background: 'var(--vkui--color_background_content)',
                border: '1px solid var(--vkui--color_separator_primary)',
                // Как у Card уроков (size_card_border_radius).
                borderRadius: 'var(--vkui--size_card_border_radius--regular)',
              }}
              selectType="plain"
              options={facultyOptions}
              value={selectedFaculty ? String(selectedFaculty) : ''}
              onChange={(_, v) => setSelectedFaculty(v ? Number(v) : null)}
              placeholder="Все учителя"
            />
            <CustomSelect
              style={{
                flexGrow: 1,
                flexBasis: 0,
                minWidth: 0,
                background: 'var(--vkui--color_background_content)',
                border: '1px solid var(--vkui--color_separator_primary)',
                // Как у Card уроков (size_card_border_radius).
                borderRadius: 'var(--vkui--size_card_border_radius--regular)',
              }}
              selectType="plain"
              options={batchOptions}
              value={selectedBatch ? String(selectedBatch) : ''}
              onChange={(_, v) => setSelectedBatch(v ? Number(v) : null)}
              placeholder="Все классы"
            />
          </Flex>
        )}

        {loading ? (
          <Flex padding="m" align="center" justify="center">
            <Spinner />
          </Flex>
        ) : lessons.length > 0 ? (
          // Слоты таймлайна — КАРТОЧКИ НА ФОНЕ ПАНЕЛИ (просьба Миши
          // 2026-09-16): каждая карточка несёт свой фон/тень/скругление,
          // поэтому общий контейнер прозрачный (белая подложка под белыми
          // карточками «съедала» объём — выглядело слитно и сжато).
          <Box paddingInline="s">
            <div style={{
              // Вертикальные отступы блока: сверху 5px (как pad слота),
              // снизу 10px, чтобы тень последней карточки не резалась.
              padding: '5px 0 10px',
            }}>
              {isAdmin && !selectedFaculty && !selectedBatch ? (
                // Админ без фильтров: вся школа — слоты-аккордеоны
                // (раскрыт текущий), как раньше.
                <TimedGroups
                  lessons={lessons}
                  isToday={isToday}
                  resetKey={globalDate}
                  onOpenLesson={onOpenLesson}
                />
              ) : (
                // Ученик/родитель/учитель/админ с фильтром: таймлайн дня
                // (мокап stitch-main-timeline.html «Расписание»).
                // onOpenLesson идёт по sheet_id — у ученика/родителя его
                // нет, клики просто не рисуются.
                <TimetableTimeline
                  lessons={lessons}
                  isToday={isToday}
                  showBatch={isAdmin}
                  onOpenLesson={onOpenLesson}
                />
              )}
            </div>
          </Box>
        ) : (
          <Placeholder icon={<Icon56CalendarOutline />}>
            <Text weight="2">Занятий не найдено</Text>
            <Text color="secondary">
              На {formatDate(globalDate)} расписание отсутствует или все уроки отменены.
            </Text>
          </Placeholder>
        )}
      </Box>

      <ModalPage
        id="timetable-calendar"
        open={calendarOpen}
        onClose={() => setCalendarOpen(false)}
        header={
          <ModalPageHeader
            before={
              <PanelHeaderButton onClick={() => setCalendarOpen(false)}>
                <Icon24Dismiss />
              </PanelHeaderButton>
            }
          >
            Выбор даты
          </ModalPageHeader>
        }
      >
        <Box padding="m">
          <Calendar
            value={new Date(globalDate + 'T00:00:00')}
            onChange={(v) => {
              if (v) {
                setGlobalDate(toISO(v as Date));
                setCalendarOpen(false);
              }
            }}
            disablePickers={false}
          />
        </Box>
      </ModalPage>
    </Panel>
  );
};
