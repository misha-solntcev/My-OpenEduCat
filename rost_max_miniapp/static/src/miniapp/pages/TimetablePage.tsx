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
  DateInput,
  CustomSelect,
  IconButton,
} from '@vkontakte/vkui';
import {
  Icon20FilterOutline,
  Icon56CalendarOutline,
} from '@vkontakte/icons';
import { useAppStore, selectGlobalDate, setGlobalDate } from '@/lib/store';
import { apiGet } from '@/lib';


interface Lesson {
  id: number;
  subject: string;
  batch: string;
  timing: string;
  faculty: string;
}

interface Faculty {
  id: number;
  name: string;
}

interface TimetableResponse {
  lessons: Lesson[];
}

interface FacultiesResponse {
  faculties: Faculty[];
}

export const TimetablePage: React.FC<{ id: string; onOpenLesson: (id: number) => void }> = ({ id, onOpenLesson }) => {
  const globalDate = useAppStore(selectGlobalDate);
  const filters = useAppStore(s => s.filters);
  const setFilters = useAppStore(s => s.setFilters);
  const selectedFaculty = filters.selectedFaculty;

  const [lessons, setLessons] = React.useState<Lesson[]>([]);
  const [faculties, setFaculties] = React.useState<Faculty[]>([]);
  const [isAdmin, setIsAdmin] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [showFilters, setShowFilters] = React.useState(false);

  React.useEffect(() => {
    apiGet<FacultiesResponse>('/rost_max/api/faculties')
      .then(data => {
        if (data.faculties?.length) {
          setFaculties(data.faculties);
          setIsAdmin(true);
        }
      })
      .catch(err => console.error('Failed to load faculties:', err));
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
    } finally {
      setLoading(false);
    }
  }, [globalDate, selectedFaculty]);

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

  const handleDateChange = (date: Date | null) => {
    if (date) {
      setGlobalDate(date.toISOString().split('T')[0]);
    }
  };

  const facultyOptions = [
    { value: null, label: 'Все учителя' },
    ...faculties.map(f => ({ value: String(f.id), label: f.name })),
  ];

  return (
      <Panel id={id}>
        <PanelHeader
          after={
            <>
              {isAdmin && (
                <IconButton
                  label="Фильтры"
                  onClick={() => setShowFilters(!showFilters)}
                >
                  <Icon20FilterOutline />
                </IconButton>
              )}
            </>
          }
        >
          Расписание
        </PanelHeader>

        <Box padding="m">
          {showFilters && isAdmin && (
            <Flex gap={4} justify="end">
              <DateInput
                mode="plain"
                value={new Date(globalDate)}
                onChange={handleDateChange}
                size="s"
                placeholder={formatDate(globalDate)}
              />
              <CustomSelect
                selectType="plain"
                options={facultyOptions}
                value={selectedFaculty ? String(selectedFaculty) : null}
                onChange={(_, v) => setFilters({ selectedFaculty: v ? Number(v) : null })}
                placeholder="Выбрать учителя"
              />
            </Flex>
          )}

          {loading ? (
            <Flex style={{ padding: '24px 0' }} align="center" justify="center">
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
              <Text weight="2" style={{ marginBottom: 8 }}>Занятий не найдено</Text>
              <Text style={{ color: 'var(--vkui--color_text_secondary)' }}>
                На {formatDate(globalDate)} расписание отсутствует или все уроки отменены.
              </Text>
            </Placeholder>
          )}
        </Box>
      </Panel>
    );
  };