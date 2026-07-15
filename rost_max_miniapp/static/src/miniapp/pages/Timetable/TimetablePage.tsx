import React from 'react';
import { Flex, Typography, Spinner, Dot, CellList, CellSimple } from '@maxhub/max-ui';
import { useAppStore } from '../../lib/store';
import { apiGet } from '../../lib';
import { DateJumper } from '../../components/DateJumper';

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
  const globalDate = useAppStore(s => s.getGlobalDate());
  const setGlobalDate = useAppStore(s => s.setGlobalDate);
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

      {/* Список занятий — нативный CellList (full-width: без боковых отступов, вписывается в 16px-обёртку страницы) */}
      {loading ? (
        <Flex style={{ padding: '24px 0' }} align="center" justify="center">
          <Spinner />
        </Flex>
      ) : lessons.length > 0 ? (
        <CellList mode="island" style={{ flex: 1, width: '100%', paddingBottom: '80px' }}>
          {lessons.map(l => (
            <CellSimple
              key={l.id}
              onClick={() => openLesson(l.id)}
              showChevron
              before={l.timing ? l.timing.split(' - ')[0] || l.timing : ''}
              title={
                <Flex align="center" gap={8}>
                  <Dot appearance="themed" />
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
        </CellList>
      ) : (
        <CellList mode="full-width" style={{ paddingBottom: '80px' }}>
          <CellSimple
            disabled
            before={<span className="rm-empty-icon">🍃</span>}
            title={
              <Typography.Title style={{ margin: 0, fontWeight: 600 }}>
                Занятий не найдено
              </Typography.Title>
            }
            subtitle={
              <Typography.Body style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>
                На {globalDate} расписание отсутствует или все уроки отменены.
              </Typography.Body>
            }
          />
        </CellList>
      )}
    </Flex>
  );
};
