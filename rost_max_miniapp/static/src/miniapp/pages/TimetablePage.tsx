import React from 'react';
import { Flex, Typography, Spinner } from '@maxhub/max-ui';
import { apiGet } from '../api';

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
}

interface FacultiesResponse {
  faculties: Faculty[];
}

// Выбор фильтров (дата + преподаватель) храним в рамках сессии:
// sessionStorage живёт при reload и переходах по history внутри одной вкладки,
// но сбрасывается при закрытии миниаппа. Этим возврат из журнала урока
// (полная навигация по URL) попадает в уже настроенный список занятий.
const TIMETABLE_FILTERS_KEY = 'rost_max_timetable_filters';

function loadFilters(): { date: string; selectedFaculty: number | null } {
  const fallback = {
    date: new Date().toISOString().split('T')[0],
    selectedFaculty: null as number | null,
  };
  try {
    const saved = sessionStorage.getItem(TIMETABLE_FILTERS_KEY);
    if (!saved) return fallback;
    const parsed = JSON.parse(saved);
    return {
      date: typeof parsed.date === 'string' && parsed.date ? parsed.date : fallback.date,
      selectedFaculty:
        parsed.selectedFaculty === undefined || parsed.selectedFaculty === null
          ? null
          : Number(parsed.selectedFaculty),
    };
  } catch {
    return fallback;
  }
}

function saveFilters(date: string, selectedFaculty: number | null) {
  try {
    sessionStorage.setItem(TIMETABLE_FILTERS_KEY, JSON.stringify({ date, selectedFaculty }));
  } catch {
    // sessionStorage может быть недоступен (приватный режим) — игнорируем
  }
}

export const TimetablePage: React.FC<TimetablePageProps> = ({ onOpenLesson }) => {
  const initial = loadFilters();
  const [date, setDate] = React.useState(initial.date);
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

  // Сохраняем выбор фильтров в рамках сессии, чтобы при возврате из журнала
  // урока (полная навигация по URL) список занятий открывался уже настроенным.
  React.useEffect(() => {
    saveFilters(date, selectedFaculty);
  }, [date, selectedFaculty]);

  const loadLessons = React.useCallback(async () => {
    setLoading(true);
    try {
      let url = `/rost_max/api/timetable?date=${date}`;
      if (selectedFaculty) url += `&faculty_id=${selectedFaculty}`;
      const data = await apiGet<TimetableResponse>(url);
      setLessons(data.lessons || []);
    } catch {
      setLessons([]);
    } finally {
      setLoading(false);
    }
  }, [date, selectedFaculty]);

  React.useEffect(() => { loadLessons(); }, [loadLessons]);

  const openLesson = (lessonId: number) => {
    onOpenLesson(lessonId);
  };

  return (
    <Flex direction="column" align="stretch" gap={12} style={{ width: '100%', height: '100%' }}>
      {/* Карточка с фильтрами */}
      <div
        style={{
          backgroundColor: 'var(--background-surface-card)',
          padding: '14px',
          borderRadius: '12px',
          border: '1px solid var(--border-neutral-subtle)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
        }}
      >
        <Flex direction="column" align="stretch" gap={10}>
          {isAdmin && faculties.length > 0 && (
            <Flex direction="column" align="stretch" gap={4}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500, marginLeft: '4px' }}>
                Преподаватель
              </span>
              <select
                value={selectedFaculty || ''}
                onChange={e => setSelectedFaculty(e.target.value ? parseInt(e.target.value) : null)}
                style={{
                  width: '100%',
                  height: '38px',
                  padding: '0 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-neutral-default)',
                  backgroundColor: 'var(--background-surface-card)',
                  color: 'var(--text-default)',
                  fontSize: '14px',
                  outline: 'none'
                }}
              >
                <option value="">Все преподаватели</option>
                {faculties.map(f => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </Flex>
          )}

          <Flex direction="column" align="stretch" gap={4}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500, marginLeft: '4px' }}>
              Дата занятий
            </span>
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              style={{
                width: '100%',
                height: '38px',
                padding: '0 12px',
                borderRadius: '8px',
                border: '1px solid var(--border-neutral-default)',
                backgroundColor: 'var(--background-surface-card)',
                color: 'var(--text-default)',
                fontSize: '14px',
                outline: 'none',
                fontFamily: 'inherit'
              }}
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
              style={{
                backgroundColor: 'var(--background-surface-card)',
                borderRadius: '12px',
                padding: '14px 16px',
                border: '1px solid var(--border-neutral-subtle)',
                boxShadow: '0 1px 4px rgba(0,0,0,0.01)',
                width: '100%',
                boxSizing: 'border-box',
                cursor: 'pointer'
              }}
            >
              <Flex direction="column" align="stretch" gap={4} style={{ width: '100%' }}>
                <Flex align="center" gap={12} justify="space-between" style={{ width: '100%' }}>
                  <Flex align="center" gap={12}>
                    <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-default)', minWidth: '40px' }}>
                      {l.timing ? l.timing.split(' - ')[0] || l.timing : ''}
                    </span>
                    <div style={{ width: '3px', height: '20px', backgroundColor: '#007aff', borderRadius: '2px', flexShrink: 0 }} />
                    <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-default)' }}>
                      {l.subject}
                    </span>
                  </Flex>
                  {/* Добавляем фиксированную ширину контейнеру и выравнивание space-between */}
                  <Flex align="center" justify="space-between" style={{ width: '40px', flexShrink: 0 }}>
                    <div style={{ width: '3px', height: '20px', backgroundColor: '#007aff', borderRadius: '2px', flexShrink: 0 }} />
                    <div
                      style={{
                        backgroundColor: 'var(--background-neutral-subtle)',
                        color: 'var(--text-default)',
                        padding: '4px 10px',
                        borderRadius: '8px',
                        fontSize: '12px',
                        fontWeight: 700,
                        whiteSpace: 'nowrap',
                        border: '1px solid var(--border-neutral-subtle)',
                      }}
                    >
                      {l.batch}
                    </div>
                  </Flex>
                </Flex>
                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
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
          style={{
            flex: 1,
            padding: '40px 20px',
            backgroundColor: 'var(--background-surface-card)',
            borderRadius: '12px',
            border: '1px solid var(--border-neutral-subtle)',
            minHeight: '200px'
          }}
        >
          <div style={{ fontSize: '48px', marginBottom: '12px' }}>🍃</div>
          <Typography.Title style={{ margin: '0 0 4px 0', fontWeight: 600 }}>
            Занятий не найдено
          </Typography.Title>
          <Typography.Body style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
            На {date} расписание отсутствует или все уроки отменены.
          </Typography.Body>
        </Flex>
      )}
    </Flex>
  );
};