import React from 'react';
import {
  Panel,
  PanelHeader,
  Flex,
  Text,
  Spinner,
  SimpleCell,
  Box,
  Group,
  Badge,
  Placeholder,
  IconButton,
  CustomSelect,
  ModalPage,
  ModalPageHeader,
  PanelHeaderButton,
  Separator,
} from '@vkontakte/vkui';
import {
  Icon20FilterOutline,
  Icon56CalendarOutline,
  Icon24CalendarOutline,
  Icon24Dismiss,
} from '@vkontakte/icons';
import { Calendar } from '@vkontakte/vkui';
import { useAppStore, selectGlobalDate, setGlobalDate } from '@/shared/lib/store';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import type { Lesson, Faculty, TimetableResponse, FacultiesResponse } from '@/shared/lib/types';

interface TimetablePageProps {
  id: string;
  onOpenLesson: (id: number) => void;
}

type FacultyOption = { value: string; label: string };

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
  const addToast = useToast();

  const [lessons, setLessons] = React.useState<Lesson[]>([]);
  const [faculties, setFaculties] = React.useState<Faculty[]>([]);
  const [isAdmin, setIsAdmin] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [showFilters, setShowFilters] = React.useState(false);
  const [calendarOpen, setCalendarOpen] = React.useState(false);

  React.useEffect(() => {
    apiGet<FacultiesResponse>('/rost_max/api/faculties')
      .then(data => {
        if (data.faculties?.length) {
          setFaculties(data.faculties);
          setIsAdmin(true);
        }
      })
      .catch((err: unknown) => {
        console.error('Failed to load faculties:', err);
      });
  }, []);

  const loadLessons = React.useCallback(async () => {
    setLoading(true);
    try {
      let url = `/rost_max/api/timetable?date=${globalDate}`;
      if (selectedFaculty) url += `&faculty_id=${selectedFaculty}`;
      const data = await apiGet<TimetableResponse>(url);
      setLessons(data.lessons || []);
    } catch {
      setLessons([]);
      addToast('Не удалось загрузить расписание', 'error');
    } finally {
      setLoading(false);
    }
  }, [globalDate, selectedFaculty, addToast]);

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

  const facultyOptions: FacultyOption[] = [
    { value: '', label: 'Все учителя' },
    ...faculties.map(f => ({ value: String(f.id), label: f.name })),
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
      <PanelHeader
        after={
          isAdmin && (
            <IconButton
              label="Фильтры"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Icon20FilterOutline />
            </IconButton>
          )
        }
      >
        Расписание
      </PanelHeader>

      <Box padding="m">
        {/* Лента дат пн-вс + переключение недель */}
        <Flex align="center" justify="space-between">
          <IconButton
            label="Предыдущая неделя"
            onClick={() => shiftWeek(-7)}
          >
            <Text>‹</Text>
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
            onClick={() => shiftWeek(7)}
          >
            <Text>›</Text>
          </IconButton>
        </Flex>

        <DayStrip selected={globalDate} onSelect={setGlobalDate} />

        {/* Фильтры — только админ */}
        {showFilters && isAdmin && (
          <Flex gap={4} justify="end">
            <CustomSelect
              selectType="plain"
              options={facultyOptions}
              value={selectedFaculty ? String(selectedFaculty) : ''}
              onChange={(_, v) => setFilters({ selectedFaculty: v ? Number(v) : null })}
              placeholder="Выбрать учителя"
            />
          </Flex>
        )}

        {loading ? (
          <Flex padding="m" align="center" justify="center">
            <Spinner />
          </Flex>
        ) : lessons.length > 0 ? (
          <Group header="Занятия">
            {lessons.map(l => (
              <SimpleCell
                key={l.id}
                onClick={() => onOpenLesson(l.id)}
                before={formatTime(l.timing)}
                subtitle={`👤 ${l.faculty}`}
                after={<Badge mode="prominent">{l.batch}</Badge>}
              >
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
