import React from 'react';
import { Flex, Typography, IconButton, Avatar } from '@maxhub/max-ui';
import { apiGet, apiPost, initialsOf } from '../../lib';

interface Student {
  id: number;
  name: string;
  avatar: string; // data:image/...;base64,... или '' (тогда показываем инициалы)
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
  onBack: () => void;
}

// Цикл оценок: пусто → 5 → 4 → 3 → 2 → пусто
const GRADES = ['', '5', '4', '3', '2'];

// Цвет отметки посещаемости по названию типа
function attendanceColor(name?: string): string {
  if (!name) return 'var(--text-secondary)';
  const n = name.toLowerCase();
  if (n.includes('присутств') || n.includes('был') || n.includes('есть') || n.includes('да')) return 'var(--background-accent-positive)';
  if (n.includes('отсутств') || n.includes('нет') || n.includes('не ')) return 'var(--background-accent-negative)';
  if (n.includes('опозд')) return 'var(--background-accent-attention-primary)';
  return 'var(--icon-themed)';
}

function gradeColor(grade: number | null): string {
  if (grade == null) return 'var(--text-secondary)';
  if (grade >= 3.5) return 'var(--background-accent-positive)';
  if (grade >= 2.5) return 'var(--background-accent-attention-primary)';
  return 'var(--background-accent-negative)';
}

interface JournalButtonProps {
  value: string;
  active: boolean;
  activeColor: string;
  onClick: () => void;
  title?: string;
  height?: number;
  minWidth?: number;
  fontSize?: number;
  padding?: string;
  whiteSpace?: string;
}

// Единая кнопка оценки/посещаемости. Акцентный цвет передаём через inline
// CSS-переменную --jb-color (см. .rm-journal-btn--active в index.css), чтобы
// color-mix мог сделать валидный полупрозрачный фон (конкатенация `${color}18`
// с var() не работает — баг до рефактора).
const JournalButton: React.FC<JournalButtonProps> = ({
  value,
  active,
  activeColor,
  onClick,
  title,
  height = 34,
  minWidth = 34,
  fontSize = 15,
  padding,
  whiteSpace,
}) => (
  <button
    type="button"
    onClick={onClick}
    title={title}
    className={`rm-journal-btn ${active ? 'rm-journal-btn--active' : ''}`}
    style={{
      height,
      minWidth,
      fontSize,
      padding: padding ?? '0',
      whiteSpace,
      ...(active ? ({ ['--jb-color' as string]: activeColor } as React.CSSProperties) : null),
    }}
  >
    {value}
  </button>
);

export const LessonJournalPage: React.FC<LessonJournalPageProps> = ({ lessonId, onBack }) => {
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

  const cycleGrade = async (student: Student) => {
    const current = student.grade != null ? String(student.grade) : '';
    const idx = GRADES.indexOf(current);
    const next = GRADES[(idx + 1) % GRADES.length];
    const nextVal = next === '' ? null : Number(next);

    const prevGrade = student.grade;

    // Оптимистичное обновление: сразу рисуем новую оценку
    setStudents(prev => prev.map(s => s.id === student.id ? { ...s, grade: nextVal } : s));

    try {
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/lesson/${lessonId}/update`,
        { student_id: student.id, grade: nextVal }
      );
      if (res.error) {
        throw new Error(res.error);
      }
    } catch (err) {
      // Откат при ошибке бэкенда/сети — возвращаем прежнюю оценку
      setStudents(prev => prev.map(s => s.id === student.id ? { ...s, grade: prevGrade } : s));
      alert('Не удалось сохранить оценку: ' + (err instanceof Error ? err.message : 'ошибка сети'));
    }
  };

  const cycleAttendance = async (student: Student) => {
    if (!attendanceTypes.length) return;
    const curIdx = attendanceTypes.findIndex(t => t.id === student.attendance_type_id);
    const nextType = attendanceTypes[(curIdx + 1) % attendanceTypes.length];

    const prevAttendanceId = student.attendance_type_id;

    // Оптимистичное обновление: сразу рисуем новую отметку
    setStudents(prev => prev.map(s => s.id === student.id ? { ...s, attendance_type_id: nextType.id } : s));

    try {
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/lesson/${lessonId}/update`,
        { student_id: student.id, attendance_type_id: nextType.id }
      );
      if (res.error) {
        throw new Error(res.error);
      }
    } catch (err) {
      // Откат при ошибке бэкенда/сети — возвращаем прежнюю отметку
      setStudents(prev => prev.map(s => s.id === student.id ? { ...s, attendance_type_id: prevAttendanceId } : s));
      alert('Не удалось изменить отметку посещаемости: ' + (err instanceof Error ? err.message : 'ошибка сети'));
    }
  };

  const headerTitle = lesson ? (lesson.subject || 'Журнал оценок') : 'Журнал оценок';
  const headerSubtitle = lesson ? [lesson.batch, lesson.timing].filter(Boolean).join(' · ') : '';

  const header = (
    <Flex direction="column" gap={2} style={{ padding: '12px 16px', borderBottom: '1px solid var(--stroke-separator-secondary)', backgroundColor: 'var(--background-surface-card)', flexShrink: 0 }}>
      <Flex align="center" gap={12}>
        <IconButton appearance="themed" mode="tertiary" onClick={onBack}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </IconButton>
        <Typography.Title variant="small-strong" style={{ margin: 0, fontWeight: 700 }}>
          {headerTitle}
        </Typography.Title>
      </Flex>
      {headerSubtitle && (
        <Typography.Label variant="small-strong" style={{ marginLeft: '36px', color: 'var(--text-secondary)' }}>
          {headerSubtitle}
        </Typography.Label>
      )}
    </Flex>
  );

  let content: React.ReactNode;
  if (loading) {
    content = (
      <Flex align="center" justify="center" style={{ flex: 1, minHeight: '200px' }}>
        <div style={{ color: 'var(--text-secondary)' }}>Загрузка...</div>
      </Flex>
    );
  } else if (students.length === 0) {
    content = (
      <Flex
        direction="column"
        align="center"
        justify="center"
        className="rm-card rm-card--empty"
        style={{
          paddingBottom: '24px'
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '12px' }}>🍃</div>
        <Typography.Title style={{ margin: '0 0 4px 0', fontWeight: 600 }}>
          Ученики не найдены
        </Typography.Title>
        <Typography.Body style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>
          Для этого урока ещё не сформирован список посещаемости.
        </Typography.Body>
      </Flex>
    );
  } else {
    content = (
      <Flex direction="column" gap={12} style={{ width: '100%' }}>
        {students.map((student) => {
          const attendanceType = attendanceTypes.find(t => t.id === student.attendance_type_id);
          const attColor = attendanceColor(attendanceType?.name);
          const gradeSet = student.grade != null;
          const attSet = !!attendanceType;
          return (
            <div
              key={student.id}
              className="rm-card"
              style={{
                padding: '12px 14px',
              }}
            >
              <Flex align="center" gap={12} style={{ width: '100%', minWidth: 0 }}>
                {/* Колонка 1: аватар (общий для двух строк) */}
                <Avatar.Container
                  size={40}
                  form="squircle"
                >
                  <Avatar.Image
                    src={student.avatar}
                    fallback={<Avatar.Text>{initialsOf(student.name)}</Avatar.Text>}
                  />
                </Avatar.Container>

                {/* Колонка 2: две строки */}
                <Flex direction="column" gap={6} style={{ flex: 1, minWidth: 0 }}>
                  {/* Строка 1: ФИО без нумерации */}
                  <span
                    style={{
                      fontSize: '14px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {student.name}
                  </span>

                  {/* Строка 2: оценка + посещаемость */}
                  <Flex align="center" gap={8} style={{ width: '100%' }}>
                    <JournalButton
                      value={gradeSet ? String(student.grade) : '—'}
                      active={gradeSet}
                      activeColor={gradeColor(student.grade)}
                      onClick={() => cycleGrade(student)}
                    />

                    <JournalButton
                      value={attSet ? attendanceType!.name : '—'}
                      active={attSet}
                      activeColor={attColor}
                      onClick={() => cycleAttendance(student)}
                      title="Нажмите, чтобы сменить отметку посещаемости"
                      fontSize={12}
                      minWidth={34}
                      padding="0 10px"
                      whiteSpace="nowrap"
                    />
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
    <Flex direction="column" align="stretch" style={{ width: '100%', height: '100dvh' }}>
      {header}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          WebkitOverflowScrolling: 'touch',
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(128, 128, 128, 0.4) transparent',
          backgroundColor: 'var(--background-surface-ground)',
          paddingTop: '16px',
          paddingBottom: '24px'
        }}
      >
        {/* Горизонтальный паддинг — на внутреннюю обёртку, а НЕ на скролл-контейнер:
            иначе padding-right сдвигает ползунок скроллбара влево от края экрана
            и справа от ползунка остаётся пустой отступ. */}
        <div style={{ paddingLeft: '16px', paddingRight: '16px' }}>
          {content}
        </div>
      </div>
    </Flex>
  );
};
