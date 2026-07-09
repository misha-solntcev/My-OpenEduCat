import React from 'react';
import { Flex, Typography } from '@maxhub/max-ui';
import { apiGet, apiPost } from '../api';

interface Student {
  id: number;
  name: string;
  avatar: string; // data:image/...;base64,... или '' (тогда показываем инициалы)
  initials: string;
  grade: number | null;
  attendance_type_id: number | null;
}

interface AttendanceType {
  id: number;
  name: string;
}

interface LessonInfo {
  subject: string;
  batch: string;
  date: string;
  timing: string;
}

interface LessonResponse {
  lesson: LessonInfo | null;
  attendance_types: AttendanceType[];
  students: Student[];
}

interface LessonJournalPageProps {
  lessonId: number;
  lessonTitle: string;
  onBack: () => void;
}

// Цикл оценок: пусто → 5 → 4 → 3 → 2 → пусто
const GRADES = ['', '5', '4', '3', '2'];

// Цвета-заглушки для аватаров без фото (хеш от ID, как в старой версии)
const AVATAR_COLORS = ['#007aff', '#34c759', '#ff3b30', '#ff9500', '#5856d6', '#ff2d55'];

function avatarColor(id: number): string {
  return AVATAR_COLORS[id % AVATAR_COLORS.length];
}

// Цвет отметки посещаемости по названию типа
function attendanceColor(name?: string): string {
  if (!name) return 'var(--text-muted)';
  const n = name.toLowerCase();
  if (n.includes('присутств') || n.includes('был') || n.includes('есть') || n.includes('да')) return '#34c759';
  if (n.includes('отсутств') || n.includes('нет') || n.includes('не ')) return '#ff3b30';
  if (n.includes('опозд')) return '#ff9500';
  return 'var(--brand-default, #007aff)';
}

function gradeColor(grade: number | null): string {
  if (grade == null) return 'var(--text-muted)';
  if (grade >= 3.5) return '#34c759';
  if (grade >= 2.5) return '#ff9500';
  return '#ff3b30';
}

export const LessonJournalPage: React.FC<LessonJournalPageProps> = ({ lessonId, lessonTitle, onBack }) => {
  const [lesson, setLesson] = React.useState<LessonInfo | null>(null);
  const [students, setStudents] = React.useState<Student[]>([]);
  const [attendanceTypes, setAttendanceTypes] = React.useState<AttendanceType[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    apiGet<LessonResponse>(`/rost_max/api/lesson/${lessonId}/students`)
      .then(data => {
        setLesson(data.lesson || null);
        setStudents(data.students || []);
        setAttendanceTypes(data.attendance_types || []);
      })
      .catch(() => {
        setStudents([]);
        setAttendanceTypes([]);
      })
      .finally(() => setLoading(false));
  }, [lessonId]);

  const cycleGrade = (student: Student) => {
    const current = student.grade != null ? String(student.grade) : '';
    const idx = GRADES.indexOf(current);
    const next = GRADES[(idx + 1) % GRADES.length];
    const nextVal = next === '' ? null : Number(next);

    setStudents(prev => prev.map(s => s.id === student.id ? { ...s, grade: nextVal } : s));
    apiPost(`/rost_max/api/lesson/${lessonId}/update`, { student_id: student.id, grade: nextVal });
  };

  const cycleAttendance = (student: Student) => {
    if (!attendanceTypes.length) return;
    const curIdx = attendanceTypes.findIndex(t => t.id === student.attendance_type_id);
    const nextType = attendanceTypes[(curIdx + 1) % attendanceTypes.length];

    setStudents(prev => prev.map(s => s.id === student.id ? { ...s, attendance_type_id: nextType.id } : s));
    apiPost(`/rost_max/api/lesson/${lessonId}/update`, { student_id: student.id, attendance_type_id: nextType.id });
  };

  const headerTitle = lesson ? (lesson.subject || lessonTitle) : lessonTitle;
  const headerSubtitle = lesson ? [lesson.batch, lesson.timing].filter(Boolean).join(' · ') : '';

  const header = (
    <Flex direction="column" gap={2} style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-neutral-subtle)', backgroundColor: 'var(--background-surface-card)', flexShrink: 0 }}>
      <Flex align="center" gap={12}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#007aff', padding: '4px 8px 4px 0' }}>
          ⬅
        </button>
        <Typography.Title level={4} style={{ margin: 0, fontWeight: 700 }}>
          {headerTitle}
        </Typography.Title>
      </Flex>
      {headerSubtitle && (
        <Typography.Label variant="secondary" size="s" style={{ marginLeft: '36px' }}>
          {headerSubtitle}
        </Typography.Label>
      )}
    </Flex>
  );

  let content: React.ReactNode;
  if (loading) {
    content = (
      <Flex align="center" justify="center" style={{ flex: 1, minHeight: '200px' }}>
        <div style={{ color: 'var(--text-muted)' }}>Загрузка...</div>
      </Flex>
    );
  } else if (students.length === 0) {
    content = (
      <Flex
        direction="column"
        align="center"
        justify="center"
        style={{
          padding: '40px 20px',
          backgroundColor: 'var(--background-surface-card)',
          borderRadius: '12px',
          border: '1px solid var(--border-neutral-subtle)',
          minHeight: '200px'
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '12px' }}>🍃</div>
        <Typography.Title style={{ margin: '0 0 4px 0', fontWeight: 600 }}>
          Ученики не найдены
        </Typography.Title>
        <Typography.Body style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
          Для этого урока ещё не сформирован список посещаемости.
        </Typography.Body>
      </Flex>
    );
  } else {
    content = (
      <Flex direction="column" gap={12} style={{ width: '100%' }}>
        {students.map((student, index) => {
          const attendanceType = attendanceTypes.find(t => t.id === student.attendance_type_id);
          const attColor = attendanceColor(attendanceType?.name);
          const gradeSet = student.grade != null;
          const attSet = !!attendanceType;
          return (
            <div
              key={student.id}
              style={{
                backgroundColor: 'var(--background-surface-card)',
                borderRadius: '12px',
                padding: '12px 14px',
                border: '1px solid var(--border-neutral-subtle)',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                width: '100%',
                boxSizing: 'border-box',
              }}
            >
              <Flex align="center" gap={12} style={{ width: '100%', minWidth: 0 }}>
                {/* Колонка 1: аватар (общий для двух строк) */}
                {student.avatar ? (
                  <img
                    src={student.avatar}
                    alt={student.name}
                    style={{ width: 40, height: 40, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }}
                  />
                ) : (
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: '50%',
                      backgroundColor: avatarColor(student.id),
                      color: '#fff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: '15px',
                      flexShrink: 0
                    }}
                  >
                    {student.initials}
                  </div>
                )}

                {/* Колонка 2: две строки */}
                <Flex direction="column" gap={6} style={{ flex: 1, minWidth: 0 }}>
                  {/* Строка 1: ФИО без нумерации */}
                  <span
                    style={{
                      fontSize: '14px',
                      fontWeight: 600,
                      color: 'var(--text-default)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {student.name}
                  </span>

                  {/* Строка 2: оценка + посещаемость */}
                  <Flex align="center" gap={8} style={{ width: '100%' }}>
                    <button
                      onClick={() => cycleGrade(student)}
                      style={{
                        width: '34px',
                        height: '34px',
                        borderRadius: '8px',
                        border: `1px solid ${gradeSet ? gradeColor(student.grade) : 'var(--border-neutral-subtle)'}`,
                        backgroundColor: gradeSet ? `${gradeColor(student.grade)}18` : 'transparent',
                        color: gradeSet ? gradeColor(student.grade) : 'var(--text-muted)',
                        fontWeight: 700,
                        fontSize: '15px',
                        cursor: 'pointer',
                        flexShrink: 0
                      }}
                    >
                      {gradeSet ? String(student.grade) : '—'}
                    </button>

                    <button
                      onClick={() => cycleAttendance(student)}
                      title="Нажмите, чтобы сменить отметку посещаемости"
                      style={{
                        height: '34px',
                        minWidth: '34px',
                        padding: '0 10px',
                        borderRadius: '8px',
                        border: `1px solid ${attSet ? attColor : 'var(--border-neutral-subtle)'}`,
                        backgroundColor: attSet ? `${attColor}18` : 'transparent',
                        color: attSet ? attColor : 'var(--text-muted)',
                        fontWeight: 600,
                        fontSize: '12px',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                        flexShrink: 0
                      }}
                    >
                      {attSet ? attendanceType!.name : '—'}
                    </button>
                  </Flex>
                </Flex>
              </Flex>
            </div>
          );
        })}
      </Flex>
    );
  }

  return (
    <Flex direction="column" style={{ width: '100%', height: '100dvh' }}>
      {header}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          WebkitOverflowScrolling: 'touch',
          backgroundColor: 'var(--background-surface-ground)',
          padding: '16px',
          paddingBottom: '24px'
        }}
      >
        {content}
      </div>
    </Flex>
  );
};
