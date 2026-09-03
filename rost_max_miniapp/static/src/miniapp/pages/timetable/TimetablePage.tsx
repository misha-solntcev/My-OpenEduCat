import React from 'react';
import {
  Panel,
  Flex,
  Text,
  Spinner,
  SimpleCell,
  Box,
  Group,
  Badge,
  Avatar,
  Placeholder,
  IconButton,
  CustomSelect,
  ModalPage,
  ModalPageHeader,
  PanelHeaderButton,
} from '@vkontakte/vkui';
import {
  Icon24ChevronLeftOutline,
  Icon24ChevronRightOutline,
  Icon56CalendarOutline,
  Icon24CalendarOutline,
  Icon24Dismiss,
} from '@vkontakte/icons';
import { Calendar } from '@vkontakte/vkui';
import { useAppStore, selectGlobalDate, setGlobalDate } from '@/shared/lib/store';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import type { Lesson, Faculty, Batch, TimetableResponse, FacultiesResponse, BatchesResponse } from '@/shared/lib/types';

interface TimetablePageProps {
  id: string;
  onOpenLesson: (id: number) => void;
}

type SelectOption = { value: string; label: string };

/** Понедельник недели, содержащей d */
const startOfWeek = (d: Date): Date => {
  const date = new Date(d);
  const day = (date.getDay() + 6) % 7; // 0=пн ... 6=вс
  date.setDate(date.getDate() - day);
  date.setHours(0, 0, 0, 0);
  return date;
};

const toISO = (d: Date): string => {
  // Локальная дата без TZ-сдвига
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

const WEEKDAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'];

/** Лента дат пн–вс недели выбранной даты + навигация по неделям */
const DayStrip: React.FC<{ selected: string; onSelect: (iso: string) => void }> = ({ selected, onSelect }) => {
  const selDate = new Date(selected + 'T00:00:00');
  const monday = startOfWeek(selDate || new Date());
  const todayISO = toISO(new Date());

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
                {WEEKDAYS[i]}
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
  const globalDate = useAppStore(selectGlobalDate);
  const filters = useAppStore(s => s.filters);
  const setFilters = useAppStore(s => s.setFilters);
  const selectedFaculty = filters.selectedFaculty;
  const selectedBatch = filters.selectedBatch;
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

  const formatTime = (timing: string): string => {
    if (!timing) return '';
    const parts = timing.split(' - ');
    return parts[0] || timing;
  };

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
    ...batches.map(b => ({ value: String(b.id), label: b.name })),
  ];

  // Переключение недели относительно текущей выбранной даты
  const shiftWeek = (days: number) => {
    const d = new Date(globalDate + 'T00:00:00');
    d.setDate(d.getDate() + days);
    setGlobalDate(toISO(d));
  };

  const goToday = () => setGlobalDate(toISO(new Date()));

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
            (floating-ui sameWidth, dropdownAutoWidth=false по умолчанию). */}
        {isAdmin && (
          <Flex gap={8} noWrap>
            <CustomSelect
              style={{
                flexGrow: 1,
                flexBasis: 0,
                minWidth: 0,
                border: '1px solid var(--vkui--color_separator_primary)',
                borderRadius: 10,
              }}
              selectType="plain"
              options={facultyOptions}
              value={selectedFaculty ? String(selectedFaculty) : ''}
              onChange={(_, v) => setFilters({ selectedFaculty: v ? Number(v) : null })}
              placeholder="Все учителя"
            />
            <CustomSelect
              style={{
                flexGrow: 1,
                flexBasis: 0,
                minWidth: 0,
                border: '1px solid var(--vkui--color_separator_primary)',
                borderRadius: 10,
              }}
              selectType="plain"
              options={batchOptions}
              value={selectedBatch ? String(selectedBatch) : ''}
              onChange={(_, v) => setFilters({ selectedBatch: v ? Number(v) : null })}
              placeholder="Все классы"
            />
          </Flex>
        )}

        {loading ? (
          <Flex padding="m" align="center" justify="center">
            <Spinner />
          </Flex>
        ) : lessons.length > 0 ? (
          <Group
            header={
              <Text weight="2" style={{ textAlign: 'center', display: 'block' }}>
                Уроки
              </Text>
            }
          >
            {lessons.map(l => (
              // Без sheet_id (ученик/родитель) журнал недоступен —
              // урок без открытия журнала.
              <SimpleCell
                key={l.id}
                onClick={l.sheet_id ? () => onOpenLesson(l.sheet_id!) : undefined}
                before={
                  <Avatar
                    size={40}
                    src={l.faculty_avatar || undefined}
                    objectPosition="center top"
                    style={{ borderRadius: 8, flexShrink: 0 }}
                  />
                }
                subtitle={l.faculty}
                after={
                  <Badge
                    mode="new"
                    style={{
                      flexShrink: 0,
                      border: '1px solid var(--vkui--color_stroke_accent)',
                    }}
                  >
                    {l.batch}
                  </Badge>
                }
              >
                <Text weight="2" inline style={{ marginRight: 6 }}>{formatTime(l.timing)}</Text>
                {l.subject}
              </SimpleCell>
            ))}
          </Group>
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
