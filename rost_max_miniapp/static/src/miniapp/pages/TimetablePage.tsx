import React from 'react';
import {
  Flex,
  Headline,
  Text,
  Spinner,
  SimpleCell,
  Group,
  Select,
  FormLayoutGroup,
  FormItem,
} from '@vkontakte/vkui';
import { useAppStore, selectGlobalDate, setGlobalDate } from '@/lib/store';
import { apiGet } from '@/lib';
import { DateJumper } from '@/components/DateJumper';

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

type SelectOption = { value: number; label: string };

export const TimetablePage: React.FC<{ onOpenLesson: (id: number) => void }> = ({ onOpenLesson }) => {
  const globalDate = useAppStore(selectGlobalDate);
  // setGlobalDate используется в DateJumper ниже
  const filters = useAppStore(s => s.filters);
  const setFilters = useAppStore(s => s.setFilters);
  const selectedFaculty = filters.selectedFaculty;

  const [lessons, setLessons] = React.useState<Lesson[]>([]);
  const [faculties, setFaculties] = React.useState<Faculty[]>([]);
  const [isAdmin, setIsAdmin] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    apiGet<FacultiesResponse>('/rost_max/api/faculties')
      .then(data => {
        if (data.faculties?.length) {
          setFaculties(data.faculties);
          setIsAdmin(true);
        }
      })
      .catch(() => { });
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

  const openLesson = (lessonId: number) => {
    onOpenLesson(lessonId);
  };

  const facultyOptions: SelectOption[] = faculties.map(f => ({ value: f.id, label: f.name }));

  return (
    <Flex direction="column" align="stretch" gap={12} style={{ width: '100%', height: '100%' }}>
      {/* Фильтры: выбор учителя + выбор даты  */}
      <Flex direction="column" align="stretch" gap={10}>
        {isAdmin && faculties.length > 0 && (
          <Flex direction="column" align="stretch" gap={4}>
            <FormLayoutGroup>
              <FormItem top="Учитель">
                <Select
                  options={facultyOptions}
                  placeholder="Все учителя"
                  value={selectedFaculty}
                  onChange={v => setFilters({ selectedFaculty: v ? Number(v) : null })}
                  mode="default"
                />
              </FormItem>
            </FormLayoutGroup>
          </Flex>
        )}

        <Flex direction="column" align="stretch" gap={4}>
          <FormLayoutGroup>
            <FormItem top="Дата занятий">
              <DateJumper value={globalDate} onChange={setGlobalDate} />
            </FormItem>
          </FormLayoutGroup>
        </Flex>
      </Flex>

      {/* Список занятий — нативный Group + SimpleCell (full-width: без боковых отступов, вписывается в 16px-обёртку страницы) */}
      {loading ? (
        <Flex style={{ padding: '24px 0' }} align="center" justify="center">
          <Spinner />
        </Flex>
      ) : lessons.length > 0 ? (
        <Group header="Занятия" style={{ flex: 1, width: '100%', paddingBottom: '80px' }}>
          {lessons.map(l => (
            <SimpleCell
              key={l.id}
              onClick={() => openLesson(l.id)}
              chevron="always"
              before={l.timing ? l.timing.split(' - ')[0] || l.timing : ''}
              children={
                <Flex align="center" gap={8}>
                  <span style={{ color: 'var(--text-accent-themed)' }}>●</span>
                  {l.subject}
                </Flex>
              }
              subtitle={<span>👤 {l.faculty}</span>}
              after={
                <span style={{
                  backgroundColor: 'var(--background-surface-secondary)',
                  color: 'var(--text-primary)',
                  padding: '4px 10px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 700,
                  whiteSpace: 'nowrap',
                  border: '1px solid var(--stroke-separator-secondary)',
                }}>
                  {l.batch}
                </span>
              }
            />
          ))}
        </Group>
      ) : (
        <Group header="Занятия" style={{ paddingBottom: '80px' }}>
          <SimpleCell
            disabled
            before={<span style={{ fontSize: '48px' }}>🍃</span>}
            children={
              <Headline level="2" weight="2">
                Занятий не найдено
              </Headline>
            }
            subtitle={
              <Text weight="1" style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>
                На {globalDate} расписание отсутствует или все уроки отменены.
              </Text>
            }
          />
        </Group>
      )}
    </Flex>
  );
};