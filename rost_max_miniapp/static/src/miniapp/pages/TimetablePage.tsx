import React from 'react';
import { Flex, Headline, Text, Spinner, SimpleCell, Group } from '@vkontakte/vkui';
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

  return (
    <Flex direction="column" align="stretch" gap={12} style={{ width: '100%', height: '100%' }}>
      {/* Фильтры: выбор учителя + выбор даты  */}
      <Flex direction="column" align="stretch" gap={10}>
        {isAdmin && faculties.length > 0 && (
          <Flex direction="column" align="stretch" gap={4}>
            <span className="rm-field-label">
              Учитель
            </span>
            <select
              className="rm-select-native"
              value={selectedFaculty || ''}
              onChange={e => setFilters({ selectedFaculty: e.target.value ? parseInt(e.target.value) : null })}
            >
              <option value="">Все учителя</option>
              {faculties.map(f => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </Flex>
        )}

        <Flex direction="column" align="stretch" gap={4}>
          <span className="rm-field-label">
            Дата занятий
          </span>
          <DateJumper value={globalDate} onChange={setGlobalDate} />
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
                  <span>●</span>
                  {l.subject}
                </Flex>
              }
              subtitle={<span>👤 {l.faculty}</span>}
              after={
                <div className="rm-batch-badge">
                  {l.batch}
                </div>
              }
            />
          ))}
        </Group>
      ) : (
        <Group header="Занятия" style={{ paddingBottom: '80px' }}>
          <SimpleCell
            disabled
            before={<span className="rm-empty-icon">🍃</span>}
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