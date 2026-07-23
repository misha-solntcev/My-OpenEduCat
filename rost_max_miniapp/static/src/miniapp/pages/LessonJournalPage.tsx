import React from 'react';
import { Flex, Typography, IconButton, Button } from '@maxhub/max-ui';
import { apiGet, apiPost } from '@/lib';
import type { Student, AttendanceType } from '@/lib/types';
import type { GradeField } from '@/lib/colors';
import { StudentRow } from '@/components/StudentRow';
import { BulkSheet } from '@/components/BulkSheet';
import { Zap } from 'lucide-react';


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

export const LessonJournalPage: React.FC<LessonJournalPageProps> = ({ lessonId, onBack }) => {
  const [lesson, setLesson] = React.useState<LessonInfo | null>(null);
  const [students, setStudents] = React.useState<Student[]>([]);
  const [attendanceTypes, setAttendanceTypes] = React.useState<AttendanceType[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [sheetOpen, setSheetOpen] = React.useState(false);
  // Режим массового выставления в шторке: true = перезаписать ВСЕ оценки/
  // посещаемость класса, false = только ранее пустые строки.
  const [overwriteAll, setOverwriteAll] = React.useState(false);
  // Снимок студентов на момент открытия шторки (baseline). В режиме
  // !overwriteAll трогаем только строки, что были пусты ДО открытия
  // шторки — заполненные до этого остаются нетронутыми, а пустые
  // (и те, что мы заполнили этим сеансом) крутятся по циклу дальше.
  const baselineRef = React.useRef<Student[]>([]);
  // dirty = есть несохранённые локальные изменения (буфер отличается от сервера)
  const [dirty, setDirty] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [showExitBanner, setShowExitBanner] = React.useState(false);

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

  // Индивидуальная оценка/посещаемость в карточке: JournalButton сама крутит
  // значение по кругу и отдаёт готовый next — здесь только применяем в буфер.
  const cycleGradeField = (student: Student, field: GradeField, next: number | null) => {
    patchStudent(student.id, { [field]: next });
  };

  const cycleAttendance = (student: Student, next: number | null) => {
    patchStudent(student.id, { attendance_type_id: next });
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
  // Общий ластик в шторке: сбрасывает ВСЕ оценки и посещаемость у всего класса.
  const clearAll = () => {
    setStudents(prev => prev.map(s => ({ ...s, grade_1: null, grade_2: null, grade_3: null, attendance_type_id: null })));
    setDirty(true);
  };
  // База цикла шторки: первая строка, чья колонка ПУСТА в baseline
    // (при !overwriteAll) — чтобы массовая кнопка крутила реально изменяемое
    // (пустое) значение. Если все заполнены — берём students[0].
    const firstEditable = (field: GradeField | 'attendance_type_id'): Student | undefined => {
      if (!overwriteAll) {
        const e = students.find(s => {
          const base = baselineRef.current.find(b => b.id === s.id);
          return !base || base[field] == null;
        });
        if (e) return e;
      }
      return students[0];
    };

    // Массовая замена в шторке: мгновенно применяет выбранное значение
    // ко ВСЕМ ученикам в локальном буфере (перезапись колонки класса).
    // Список за ширмой перерисовывается сразу. Тонкая правка по карточке — индивидуально.
    // Режим overwriteAll (Switch в шторке): true = перезаписать всех,
    // false = только строки, что были ПУСТЫ до открытия шторки (baseline).
    // Заполненные до шторки остаются нетронутыми; пустые (и те, что мы
    // заполнили этим сеансом) крутятся по циклу дальше.
    const bulkSetGrade = (field: GradeField, value: number | null) => {
      setStudents(prev => prev.map(s => {
        if (!overwriteAll) {
          const base = baselineRef.current.find(b => b.id === s.id);
          // трогаем только если в baseline эта колонка была пустой
          if (!base || base[field] != null) return s;
        }
        return { ...s, [field]: value };
      }));
      setDirty(true);
    };
    // Массовая замена посещаемости: attId=null => сброс всех в «-».
    const bulkSetAtt = (attId: number | null) => {
      setStudents(prev => prev.map(s => {
        if (!overwriteAll) {
          const base = baselineRef.current.find(b => b.id === s.id);
          if (!base || base.attendance_type_id != null) return s;
        }
        return { ...s, attendance_type_id: attId };
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
          <Typography.Title variant="small-strong">
            {headerTitle}
          </Typography.Title>
        </div>
        <IconButton appearance="themed" mode="tertiary" onClick={() => { baselineRef.current = students.map(s => ({ ...s })); setSheetOpen(true); }} title="Массово проставить оценки и посещаемость" style={{ flexShrink: 0 }}>
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
        <Typography.Title>
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
        {students.map((student) => (
          <StudentRow
            key={student.id}
            student={student}
            attendanceTypes={attendanceTypes}
            onCycleGrade={cycleGradeField}
            onCycleAttendance={cycleAttendance}
          />
        ))}
      </Flex>
    );
  }


  // Простая SVG-иконка группы людей (силуэты пользователей)
  // Bottom sheet: массовая расстановка оценки + посещаемости всему классу.  
  // MAX UI v0.1.14 не имеет нативного sheet/modal -> кастомный fixed-оверлей
  // снизу. Закрытие по тапу на затемнение. Цикл кнопок тот же, что у
  // BulkSheet вынесен в отдельный компонент components/BulkSheet.

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
          <Button
            stretched
            size="large"
            mode="primary"
            appearance="themed"
            loading={saving}
            onClick={saveAll}
          >
            Сохранить
          </Button>
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
              <Button
                stretched
                size="large"
                mode="primary"
                appearance="themed"
                loading={saving}
                onClick={exitSave}
              >
                Да, сохранить
              </Button>
              <Button
                stretched
                size="large"
                mode="secondary"
                loading={saving}
                onClick={exitDiscard}
              >
                Нет, не сохранять
              </Button>
              <Button
                stretched
                size="large"
                mode="tertiary"
                onClick={() => setShowExitBanner(false)}
              >
                Остаться
              </Button>
            </Flex>
          </div>
        </div>
      )}

      {sheetOpen && (
        <BulkSheet
          students={students}
          attendanceTypes={attendanceTypes}
          overwriteAll={overwriteAll}
          onOverwriteAllChange={setOverwriteAll}
          firstEditable={firstEditable}
          onBulkGrade={bulkSetGrade}
          onBulkAtt={bulkSetAtt}
          onClearAll={clearAll}
          onClose={() => setSheetOpen(false)}
        />
      )}
    </Flex>
  );
};
