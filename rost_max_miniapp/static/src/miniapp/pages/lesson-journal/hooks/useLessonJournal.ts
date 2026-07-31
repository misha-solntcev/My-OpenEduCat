import React from 'react';
import { apiGet } from '@/shared/lib/api';
import { apiPost } from '@/shared/lib/api';
import type { Student, AttendanceType, GradeField } from '@/shared/lib/types';

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

interface UseLessonJournalReturn {
  lesson: LessonInfo | null;
  students: Student[];
  attendanceTypes: AttendanceType[];
  loading: boolean;
  error: string | null;
  dirty: boolean;
  saving: boolean;
  showExitBanner: boolean;
  setShowExitBanner: (v: boolean) => void;
  cycleGradeField: (student: Student, field: GradeField, next: number | null) => void;
  cycleAttendance: (student: Student, next: number | null) => void;
  saveAll: () => Promise<void>;
  handleBack: () => void;
  exitSave: () => Promise<void>;
  exitDiscard: () => void;
  loadStudents: () => void;
  // Массовые операции для BulkSheet
  bulkSetGrade: (field: GradeField, value: number | null, overwriteFilled: boolean, baselineRef: React.MutableRefObject<Student[]>) => void;
  bulkSetAtt: (attId: number | null, overwriteFilled: boolean, baselineRef: React.MutableRefObject<Student[]>) => void;
  clearAll: () => void;
}

/**
 * Хук бизнес-логики журнала урока:
 * - загрузка учеников/типов посещаемости
 * - локальный буфер изменений (dirty-трекинг)
 * - сохранение на сервер (через Toast, не alert)
 * - обработка выхода с несохранёнными правками
 * - массовые операции для BulkSheet
 */
export function useLessonJournal(lessonId: number | null, onBack: () => void): UseLessonJournalReturn {
  const [lesson, setLesson] = React.useState<LessonInfo | null>(null);
  const [students, setStudents] = React.useState<Student[]>([]);
  const [attendanceTypes, setAttendanceTypes] = React.useState<AttendanceType[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dirty, setDirty] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [showExitBanner, setShowExitBanner] = React.useState(false);

  const loadStudents = React.useCallback(() => {
    if (!lessonId) {
      setLesson(null);
      setStudents([]);
      setAttendanceTypes([]);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    apiGet<LessonResponse>(`/rost_max/api/lesson/${lessonId}/students`)
      .then(data => {
        setLesson(data.lesson || null);
        setStudents(data.students || []);
        setAttendanceTypes(data.attendance_types || []);
        setDirty(false);
      })
      .catch(() => {
        setStudents([]);
        setAttendanceTypes([]);
        setError('Не удалось загрузить данные урока');
      })
      .finally(() => setLoading(false));
  }, [lessonId]);

  React.useEffect(() => { loadStudents(); }, [loadStudents]);

  const patchStudent = (id: number, patch: Partial<Student>) => {
    setStudents(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s));
    setDirty(true);
  };

  const cycleGradeField = (student: Student, field: GradeField, next: number | null) => {
    patchStudent(student.id, { [field]: next });
  };

  const cycleAttendance = (student: Student, next: number | null) => {
    patchStudent(student.id, { attendance_type_id: next });
  };

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
    } catch {
      setError('Не удалось сохранить. Изменения сохранены локально, повторите позже.');
    } finally {
      setSaving(false);
    }
  };

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

  const bulkSetGrade = (field: GradeField, value: number | null, overwriteFilled: boolean, baselineRef: React.MutableRefObject<Student[]>) => {
    setStudents(prev => prev.map(s => {
      if (!overwriteFilled) {
        const base = baselineRef.current.find(b => b.id === s.id);
        if (base && base[field] != null) return s;
      }
      return { ...s, [field]: value };
    }));
    setDirty(true);
  };

  const bulkSetAtt = (attId: number | null, overwriteFilled: boolean, baselineRef: React.MutableRefObject<Student[]>) => {
    setStudents(prev => prev.map(s => {
      if (!overwriteFilled) {
        const base = baselineRef.current.find(b => b.id === s.id);
        if (base && base.attendance_type_id != null) return s;
      }
      return { ...s, attendance_type_id: attId };
    }));
    setDirty(true);
  };

  const clearAll = () => {
    setStudents(prev => {
      const next = prev.map(s => ({
        ...s, grade_1: null, grade_2: null, grade_3: null, attendance_type_id: null,
      }));
      const hasChanges = next.some((s, i) => {
        const o = prev[i];
        return s.grade_1 !== o.grade_1
          || s.grade_2 !== o.grade_2
          || s.grade_3 !== o.grade_3
          || s.attendance_type_id !== o.attendance_type_id;
      });
      if (hasChanges) setDirty(true);
      return next;
    });
  };

  return {
    lesson,
    students,
    attendanceTypes,
    loading,
    error,
    dirty,
    saving,
    showExitBanner,
    setShowExitBanner,
    cycleGradeField,
    cycleAttendance,
    saveAll,
    handleBack,
    exitSave,
    exitDiscard,
    loadStudents,
    bulkSetGrade,
    bulkSetAtt,
    clearAll,
  };
}