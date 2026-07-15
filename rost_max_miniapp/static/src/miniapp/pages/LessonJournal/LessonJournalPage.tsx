import React from 'react';
import { Flex, Typography, IconButton, Avatar } from '@maxhub/max-ui';
import { apiGet, apiPost, initialsOf } from '../../lib';
import { Users, Zap, Eraser } from 'lucide-react';

interface Student {
  id: number;
  name: string;
  avatar: string; // data:image/...;base64,... или '' (тогда показываем инициалы)
  grade_1: number | null;
  grade_2: number | null;
  grade_3: number | null;
  attendance_type_id: number | null;
}

// Колонки оценок (соответствуют полям модели op.attendance.line)
type GradeField = 'grade_1' | 'grade_2' | 'grade_3';
const GRADE_FIELDS: GradeField[] = ['grade_1', 'grade_2', 'grade_3'];
const GRADE_FIELD_LABELS: Record<GradeField, string> = {
  grade_1: 'О1',
  grade_2: 'О2',
  grade_3: 'О3',
};

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
  flex?: number;
}

// Единая кнопка оценки/посещаемости. Акцентный цвет передаём через inline
// CSS-переменную --jb-color (см. .rm-journal-btn--active в style.css), чтобы
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
  flex,
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
      flex,
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
  const [sheetOpen, setSheetOpen] = React.useState(false);
  // dirty = есть несохранённые локальные изменения (буфер отличается от сервера)
  const [dirty, setDirty] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [showExitBanner, setShowExitBanner] = React.useState(false);
  // Режим массовой карусели: 'empty' (только пустые) | 'all' (перезапись всех)
  const [bulkMode, setBulkMode] = React.useState<'empty' | 'all'>('empty');

  const loadStudents = React.useCallback(() => {
    setLoading(true);
    apiGet<LessonResponse>(`/rost_max/api/lesson/${lessonId}/students`)
      .then(data => {
        setLesson(data.lesson || null);
        setStudents(data.students || []);
        setAttendanceTypes(data.attendance_types || []);
        // Свежие данные с сервера = буфер чистый
        setDirty(false);
      })
      .catch(() => {
        setStudents([]);
        setAttendanceTypes([]);
      })
      .finally(() => setLoading(false));
  }, [lessonId]);

  React.useEffect(() => { loadStudents(); }, [loadStudents]);

  // Локальное изменение буфера (без обращения к серверу). Ставит dirty.
  const patchStudent = (id: number, patch: Partial<Student>) => {
    setStudents(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s));
    setDirty(true);
  };

  // Индивидуальная оценка/посещаемость в карточке: только меняем буфер.
  const cycleGradeField = (student: Student, field: GradeField) => {
    const current = student[field] != null ? String(student[field]) : '';
    const idx = GRADES.indexOf(current);
    const next = GRADES[(idx + 1) % GRADES.length];
    const nextVal = next === '' ? null : Number(next);
    patchStudent(student.id, { [field]: nextVal });
  };

  const cycleAttendance = (student: Student) => {
    if (!attendanceTypes.length) return;
    const curIdx = attendanceTypes.findIndex(t => t.id === student.attendance_type_id);
    const nextType = attendanceTypes[(curIdx + 1) % attendanceTypes.length];
    patchStudent(student.id, { attendance_type_id: nextType.id });
  };

  // Сохранение всего буфера на сервер одним запросом (/save, перезапись).
  const saveAll = async () => {
    if (saving || !dirty) return;
    setSaving(true);
    try {
      const payload = students.map(s => ({
        student_id: s.id,
        grade_1: s.grade_1,
        grade_2: s.grade_2,
        grade_3: s.grade_3,
        attendance_type_id: s.attendance_type_id,
      }));
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/lesson/${lessonId}/save`,
        { students: payload }
      );
      if (res.error) throw new Error(res.error);
      setDirty(false);
      // Перечитываем с сервера для консистентности (проверка, что записано)
      loadStudents();
    } catch (err) {
      // Сети нет или ошибка сервера: предупреждаем, dirty остаётся.
      // (Офлайн-синхронизация через локальный стор — отдельная фича, позже.)
      alert('Не удалось сохранить: ' + (err instanceof Error ? err.message : 'ошибка сети') + '. Изменения сохранены локально, повторите позже.');
    } finally {
      setSaving(false);
    }
  };

  // Выход: если есть несохранённые правки — банер «Сохранить изменения?».
  const handleBack = () => {
    if (dirty) {
      setShowExitBanner(true);
    } else {
      onBack();
    }
  };
  const exitSave = async () => {
    setShowExitBanner(false);
    await saveAll();
    onBack();
  };
  const exitDiscard = () => {
    setShowExitBanner(false);
    setDirty(false);
    onBack();
  };

  // Ластик колонки в шторке: локально сбрасывает колонку в буфере.
  const clearLocal = (target: GradeField | 'attendance') => {
    setStudents(prev => prev.map(s => {
      if (target === 'attendance') return { ...s, attendance_type_id: null };
      return { ...s, [target]: null };
    }));
    setDirty(true);
  };
  // Массовая карусель в шторке: мгновенно (как ластик) применяет
  // выбранное значение ко ВСЕМ ученикам в локальном буфере.
  // bulkMode: 'empty' — только пустые колонки; 'all' — перезапись всех.
  // Список за ширмой перерисовывается сразу.
  const bulkSetGrade = (field: GradeField, value: string) => {
    const v = value === '' ? null : Number(value);
    setStudents(prev => prev.map(s => {
      if (bulkMode === 'empty' && s[field] != null) return s;
      return { ...s, [field]: v };
    }));
    setDirty(true);
  };
  const bulkCycleGrade = (field: GradeField) => {
    // курсор карусели: при 'empty' — первый пустой; при 'all' — первый вообще
    const cursorSrc = bulkMode === 'empty'
      ? students.find(s => s[field] == null)
      : students[0];
    const current = cursorSrc?.[field] != null ? String(cursorSrc[field]) : '';
    const idx = GRADES.indexOf(current);
    const next = GRADES[(idx + 1) % GRADES.length];
    bulkSetGrade(field, next);
  };
  const bulkCycleAtt = () => {
    if (!attendanceTypes.length) return;
    const cursorSrc = bulkMode === 'empty'
      ? students.find(s => !s.attendance_type_id)
      : students[0];
    const curIdx = cursorSrc && cursorSrc.attendance_type_id != null
      ? attendanceTypes.findIndex(t => t.id === cursorSrc.attendance_type_id)
      : -1;
    const nextType = attendanceTypes[(curIdx + 1) % attendanceTypes.length];
    setStudents(prev => prev.map(s => {
      if (bulkMode === 'empty' && s.attendance_type_id != null) return s;
      return { ...s, attendance_type_id: nextType.id };
    }));
    setDirty(true);
  };

  const headerTitle = lesson ? (lesson.subject || 'Журнал оценок') : 'Журнал оценок';
  const headerSubtitle = lesson ? [lesson.batch, lesson.timing].filter(Boolean).join(' · ') : '';

  const header = (
    <Flex direction="column" gap={2} style={{ padding: '12px 16px', borderBottom: '1px solid var(--stroke-separator-secondary)', backgroundColor: 'var(--background-surface-card)', flexShrink: 0 }}>
      <Flex align="center" gap={12} style={{ width: '100%' }}>
        <IconButton appearance="themed" mode="tertiary" onClick={handleBack}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </IconButton>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Typography.Title variant="small-strong" style={{ margin: 0, fontWeight: 700 }}>
            {headerTitle}
          </Typography.Title>
        </div>
        <IconButton appearance="themed" mode="tertiary" onClick={() => setSheetOpen(true)} title="Массово проставить оценки и посещаемость" style={{ flexShrink: 0 }}>
          <Zap size={20} color="currentColor" />
        </IconButton>
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
          const gradeFields: { field: GradeField; value: number | null }[] = [
            { field: 'grade_1', value: student.grade_1 },
            { field: 'grade_2', value: student.grade_2 },
            { field: 'grade_3', value: student.grade_3 },
          ];
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

                  {/* Строка 2: три оценки + посещаемость */}
                  <Flex align="center" gap={6} wrap="wrap" style={{ width: '100%' }}>
                    {gradeFields.map(({ field, value }) => (
                      <JournalButton
                        key={field}
                        value={value != null ? String(value) : '—'}
                        active={value != null}
                        activeColor={gradeColor(value)}
                        onClick={() => cycleGradeField(student, field)}
                        title={`Оценка ${GRADE_FIELD_LABELS[field]}`}
                        minWidth={30}
                        padding="0 6px"
                      />
                    ))}

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


  // Простая SVG-иконка группы людей (силуэты пользователей)
  // Bottom sheet: массовая расстановка оценки + посещаемости всему классу.  
  // MAX UI v0.1.14 не имеет нативного sheet/modal -> кастомный fixed-оверлей
  // снизу. Закрытие по тапу на затемнение. Цикл кнопок тот же, что у
  // индивидуальных (GRADES / attendanceTypes).
  const bulkSheet = sheetOpen && (
    <div
      onClick={() => setSheetOpen(false)}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.4)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'flex-end',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%',
          backgroundColor: 'var(--background-surface-card)',
          borderTopLeftRadius: '16px',
          borderTopRightRadius: '16px',
          padding: '20px 16px calc(20px + env(safe-area-inset-bottom))',
          boxSizing: 'border-box',
          animation: 'rm-sheet-up 0.2s ease-out',
        }}
      >
        <Flex direction="column" gap={20}>
          {/* Режим массовой карусели: только пустые | перезапись всех */}
          <Flex
            align="center"
            gap={4}
            style={{
              width: '100%',
              padding: '4px',
              borderRadius: '10px',
              backgroundColor: 'var(--background-surface-raised)',
            }}
          >
            {([
              { mode: 'empty' as const, label: 'Только пустые' },
              { mode: 'all' as const, label: 'Все' },
            ]).map(({ mode, label }) => (
              <button
                key={mode}
                type="button"
                onClick={() => setBulkMode(mode)}
                style={{
                  flex: 1,
                  height: '34px',
                  borderRadius: '8px',
                  border: 'none',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: 'pointer',
                  backgroundColor: bulkMode === mode ? 'var(--background-surface-card)' : 'transparent',
                  color: bulkMode === mode ? 'var(--text-primary)' : 'var(--text-secondary)',
                  boxShadow: bulkMode === mode ? '0 1px 2px rgba(0,0,0,0.12)' : 'none',
                }}
              >
                {label}
              </button>
            ))}
          </Flex>

          {/* Сетка: аватар + для каждой колонки (О1/О2/О3/Посещ) — ластик
              сверху (иконка, без метки) и карусель снизу. Ластики выровнены
              над соответствующими оценками. Кнопки ластиков минимальной
              ширины, чтобы все 4 колонки + аватар влезали в одну строку
              на ~375px без переноса. */}
          <Flex align="flex-start" gap={8} wrap="wrap" style={{ width: '100%', minWidth: 0 }}>
            <Avatar.Container size={48} form="squircle" className="rm-sheet-avatar" style={{ flexShrink: 0, marginTop: '34px' }}>
              <Avatar.Icon>
                <Users size={22} color="var(--text-contrast-static)" />
              </Avatar.Icon>
            </Avatar.Container>

            {GRADE_FIELDS.map((gf) => (
              <Flex key={gf} direction="column" align="center" gap={6} style={{ flexShrink: 0, minWidth: 0 }}>
                <button
                  type="button"
                  onClick={() => clearLocal(gf)}
                  title={`Очистить ${GRADE_FIELD_LABELS[gf]} у всего класса`}
                  style={{
                    width: '34px',
                    height: '32px',
                    borderRadius: '8px',
                    border: '1px solid var(--stroke-separator-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    backgroundColor: 'var(--background-surface-card)',
                    color: 'var(--background-accent-negative)',
                  }}
                >
                  <Eraser size={16} color="currentColor" />
                </button>
                <JournalButton
                  value={students[0]?.[gf] != null ? String(students[0]![gf]) : '—'}
                  active={students[0]?.[gf] != null}
                  activeColor={gradeColor(students[0]?.[gf] ?? null)}
                  onClick={() => bulkCycleGrade(gf)}
                  title={`Массово: оценка ${GRADE_FIELD_LABELS[gf]} (пустые)`}
                  minWidth={30}
                  padding="0 6px"
                />
              </Flex>
            ))}

            <Flex direction="column" align="center" gap={6} style={{ flexShrink: 0, minWidth: 0 }}>
              <button
                type="button"
                onClick={() => clearLocal('attendance')}
                title="Очистить посещаемость у всего класса"
                style={{
                  width: '34px',
                  height: '32px',
                  borderRadius: '8px',
                  border: '1px solid var(--stroke-separator-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  backgroundColor: 'var(--background-surface-card)',
                  color: 'var(--background-accent-negative)',
                }}
              >
                <Eraser size={16} color="currentColor" />
              </button>
              <JournalButton
                value={(() => { const f = students.find(s => !s.attendance_type_id); return f && f.attendance_type_id != null ? attendanceTypes.find(t => t.id === f.attendance_type_id)?.name ?? '—' : '—'; })()}
                active={!!students.find(s => !s.attendance_type_id && s.attendance_type_id != null)}
                activeColor={attendanceColor(students.find(s => !s.attendance_type_id && s.attendance_type_id != null) ? attendanceTypes.find(t => t.id === students.find(s => !s.attendance_type_id)!.attendance_type_id)?.name : undefined)}
                onClick={bulkCycleAtt}
                fontSize={12}
                padding="0 10px"
                whiteSpace="nowrap"
              />
            </Flex>
          </Flex>

          {/* Одна кнопка закрытия шторки. Массовые правки (карусели
              и ластики) применяются к локальному буферу мгновенно,
              список за ширмой перерисовывается сразу. Сохранение на
              сервер — общей кнопкой «Сохранить» снизу экрана. */}
          <Flex align="center" gap={12} style={{ width: '100%' }}>
            <button
              type="button"
              onClick={() => setSheetOpen(false)}
              style={{
                flex: 1,
                height: '44px',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 600,
                fontSize: '15px',
                cursor: 'pointer',
                backgroundColor: 'var(--background-accent-themed)',
                color: 'var(--text-on-accent)',
              }}
            >
              ОК
            </button>
          </Flex>
        </Flex>
      </div>
    </div>
  );

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
          paddingBottom: dirty ? '84px' : '24px' // место под панель «Сохранить»
        }}
      >
        {/* Горизонтальный паддинг — на внутреннюю обёртку, а НЕ на скролл-контейнер:
            иначе padding-right сдвигает ползунок скроллбара влево от края экрана
            и справа от ползунка остаётся пустой отступ. */}
        <div style={{ paddingLeft: '16px', paddingRight: '16px' }}>
          {content}
        </div>
      </div>

      {/* Нижняя фикс-панель «Сохранить» — только когда есть несохранённые правки */}
      {dirty && (
        <div
          style={{
            position: 'fixed',
            left: 0,
            right: 0,
            bottom: 0,
            padding: '12px 16px calc(12px + env(safe-area-inset-bottom))',
            backgroundColor: 'var(--background-surface-card)',
            borderTop: '1px solid var(--stroke-separator-secondary)',
            zIndex: 90,
          }}
        >
          <button
            type="button"
            onClick={saveAll}
            disabled={saving}
            style={{
              width: '100%',
              height: '46px',
              borderRadius: '10px',
              border: 'none',
              fontWeight: 700,
              fontSize: '16px',
              cursor: saving ? 'not-allowed' : 'pointer',
              backgroundColor: 'var(--background-accent-themed)',
              color: 'var(--text-on-accent)',
            }}
          >
            {saving ? 'Сохраняем...' : 'Сохранить'}
          </button>
        </div>
      )}

      {/* Банер при выходе с несохранёнными правками */}
      {showExitBanner && (
        <div
          onClick={() => setShowExitBanner(false)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 200,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: '360px',
              backgroundColor: 'var(--background-surface-card)',
              borderRadius: '16px',
              padding: '20px 16px calc(16px + env(safe-area-inset-bottom))',
              boxSizing: 'border-box',
            }}
          >
            <div style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', color: 'var(--text-primary)' }}>
              Сохранить изменения?
            </div>
            <Flex direction="column" gap={10} style={{ width: '100%' }}>
              <button
                type="button"
                onClick={exitSave}
                disabled={saving}
                style={{
                  width: '100%', height: '46px', borderRadius: '10px', border: 'none',
                  fontWeight: 700, fontSize: '16px', cursor: saving ? 'not-allowed' : 'pointer',
                  backgroundColor: 'var(--background-accent-themed)', color: 'var(--text-on-accent)',
                }}
              >
                {saving ? 'Сохраняем...' : 'Да, сохранить'}
              </button>
              <button
                type="button"
                onClick={exitDiscard}
                disabled={saving}
                style={{
                  width: '100%', height: '46px', borderRadius: '10px',
                  border: '1px solid var(--stroke-separator-secondary)', fontWeight: 600, fontSize: '16px',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  backgroundColor: 'var(--background-surface-raised)', color: 'var(--text-primary)',
                }}
              >
                Нет, не сохранять
              </button>
              <button
                type="button"
                onClick={() => setShowExitBanner(false)}
                disabled={saving}
                style={{
                  width: '100%', height: '46px', borderRadius: '10px', border: 'none',
                  fontWeight: 600, fontSize: '16px', cursor: saving ? 'not-allowed' : 'pointer',
                  backgroundColor: 'transparent', color: 'var(--text-secondary)',
                }}
              >
                Остаться
              </button>
            </Flex>
          </div>
        </div>
      )}

      {bulkSheet}
    </Flex>
  );
};
