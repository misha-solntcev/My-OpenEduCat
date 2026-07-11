import React from 'react';
import { Flex, Typography, Spinner, Dot } from '@maxhub/max-ui';
import { apiGet } from '../api';
import { getSavedFilters, saveFilters } from '../utils/storage';

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

interface TimetablePageProps {
  onOpenLesson: (lessonId: number) => void;
  globalDate: string;
  onDateChange: (date: string) => void;
}

interface FacultiesResponse {
  faculties: Faculty[];
}

export const TimetablePage: React.FC<TimetablePageProps> = ({
  onOpenLesson,
  globalDate,
  onDateChange,
}) => {
  const initial = getSavedFilters();
  const [lessons, setLessons] = React.useState<Lesson[]>([]);
  const [faculties, setFaculties] = React.useState<Faculty[]>([]);
  const [selectedFaculty, setSelectedFaculty] = React.useState<number | null>(initial.selectedFaculty);
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

  // Сохраняем выбор преподавателя в рамках сессии (дата теперь единая,
  // управляется из App.tsx и пишется туда же — чтобы Date Jumper на дашборде
  // и на расписании были синхронизированы).
  React.useEffect(() => {
    saveFilters({ date: globalDate, selectedFaculty });
  }, [globalDate, selectedFaculty]);

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
      {/* Карточка с фильтрами */}
      <div
        className="rm-card"
        style={{
          padding: '14px',
        }}
      >
        <Flex direction="column" align="stretch" gap={10}>
          {isAdmin && faculties.length > 0 && (
            <Flex direction="column" align="stretch" gap={4}>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500, marginLeft: '4px' }}>
                Преподаватель
              </span>
              <select
                value={selectedFaculty || ''}
                onChange={e => setSelectedFaculty(e.target.value ? parseInt(e.target.value) : null)}
                className="rm-select"
              >
                <option value="">Все преподаватели</option>
                {faculties.map(f => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </Flex>
          )}

          <Flex direction="column" align="stretch" gap={4}>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500, marginLeft: '4px' }}>
              Дата занятий
            </span>
            <input
              type="date"
              value={globalDate}
              onChange={e => onDateChange(e.target.value)}
              className="rm-input"
            />
          </Flex>
        </Flex>
      </div>

      {/* Список занятий */}
      {loading ? (
        <Flex style={{ padding: '24px 0' }} align="center" justify="center">
          <Spinner />
        </Flex>
      ) : lessons.length > 0 ? (
        <Flex
          direction="column"
          align="stretch"
          gap={12}
          style={{
            flex: 1,
            width: '100%',
            paddingBottom: '80px'
          }}
        >
          {lessons.map(l => (
            <div
              key={l.id}
              onClick={() => openLesson(l.id)}
              className="rm-card rm-card--tight"
            >
              <Flex direction="column" align="stretch" gap={4} style={{ width: '100%' }}>
                <Flex align="center" gap={12} justify="space-between" style={{ width: '100%' }}>
                  <Flex align="center" gap={12}>
                    <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', minWidth: '40px' }}>
                      {l.timing ? l.timing.split(' - ')[0] || l.timing : ''}
                    </span>
                    <Dot appearance="themed" />
                    <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {l.subject}
                    </span>
                  </Flex>
                  {/* Добавляем фиксированную ширину контейнеру и выравнивание space-between */}
                  <Flex align="center" justify="space-between" style={{ width: '40px', flexShrink: 0 }}>
                    <Dot appearance="themed" />
                    <div
                      style={{
                        backgroundColor: 'var(--background-surface-secondary)',
                        color: 'var(--text-primary)',
                        padding: '4px 10px',
                        borderRadius: '8px',
                        fontSize: '12px',
                        fontWeight: 700,
                        whiteSpace: 'nowrap',
                        border: '1px solid var(--stroke-separator-secondary)',
                      }}
                    >
                      {l.batch}
                    </div>
                  </Flex>
                </Flex>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  👤 {l.faculty}
                </span>
              </Flex>
            </div>
          ))}
        </Flex>
      ) : (
        <Flex
          direction="column"
          align="center"
          justify="center"
          className="rm-card rm-card--empty"
          style={{
            paddingBottom: '80px'
          }}
        >
          <div style={{ fontSize: '48px', marginBottom: '12px' }}>🍃</div>
          <Typography.Title style={{ margin: '0 0 4px 0', fontWeight: 600 }}>
            Занятий не найдено
          </Typography.Title>
          <Typography.Body style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>
            На {globalDate} расписание отсутствует или все уроки отменены.
          </Typography.Body>
        </Flex>
      )}
    </Flex>
  );
};