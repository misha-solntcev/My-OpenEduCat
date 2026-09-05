import React from 'react';
import {
  Panel,
  Flex,
  Text,
  Spinner,
  Box,
  Placeholder,
  IconButton,
  CustomSelect,
  ModalPage,
  ModalPageHeader,
  PanelHeaderButton,
  Card,
} from '@vkontakte/vkui';
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
import { LessonRow, lessonStatus } from '@/shared/components/LessonRow';
import { TimedGroups } from '@/shared/components/TimedGroups';
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
          // Список в карточке (Card mode="shadow" — фон/скругление/тень
          // по умолчанию VKUI): Group в MAX WebView рендерится plain и
          // прилипает к краям экрана без отступов. Заголовок «Уроки» —
          // НАД карточкой: header внутри Group красит полосу белым и
          // обрезает верхнее скругление Card.
          <Box paddingInline="s">
            <Card mode="shadow" style={{ overflow: 'hidden' }}>
              {/* Заголовок ВНУТРИ Card (без Group!): у .vkuiGroup__host:
                  first-of-type в VKUI жёсткое border-top-*-radius: 0 —
                  Group съедает верхнее скругление Card. */}
              <Text weight="2" style={{ textAlign: 'center', display: 'block', padding: '12px 16px 8px' }}>
                Уроки
              </Text>
              {isAdmin && !selectedFaculty && !selectedBatch ? (
                // Без фильтров: слоты по таймингу, раскрыт текущий.
                // С фильтром (учитель/класс) записей мало — плоский список,
                // аккордеоны только мешают (каждый слот надо открывать).
                <TimedGroups
                  lessons={lessons}
                  isToday={isToday}
                  resetKey={globalDate}
                  onOpenLesson={onOpenLesson}
                />
              ) : (
                lessons.map(l => (
                  // Без sheet_id (ученик/родитель) журнал недоступен —
                  // урок без открытия журнала.
                  <LessonRow
                    key={l.id}
                    lesson={l}
                    status={lessonStatus(l.timing, isToday)}
                    showBatch
                    showFaculty
                    onClick={l.sheet_id ? () => onOpenLesson(l.sheet_id!) : undefined}
                  />
                ))
              )}
            </Card>
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
