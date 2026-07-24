import React from 'react';
import type { Student, AttendanceType } from '@/lib/types';
import type { GradeField } from '@/lib/colors';

interface UseBulkSheetReturn {
  overwriteFilled: boolean;
  setOverwriteFilled: (v: boolean) => void;
  baselineRef: React.MutableRefObject<Student[]>;
  firstEditable: (field: GradeField | 'attendance_type_id') => Student | undefined;
  bulkSetGrade: (field: GradeField, value: number | null) => void;
  bulkSetAtt: (attId: number | null) => void;
  clearAll: () => void;
  resetBaseline: (students: Student[]) => void;
}

/**
 * Хук логики массовой шторки (BulkSheet):
 * - overwriteFilled (перезаписывать заполненные / только пустые)
 * - baselineRef (снимок студентов на момент открытия шторки)
 * - firstEditable (поиск первой редактируемой строки для базового значения кнопки)
 * - bulkSetGrade / bulkSetAtt / clearAll (массовые действия над буфером)
 * - resetBaseline (обновление снапшота baseline при открытии шторки)
 */
export function useBulkSheet(
  students: Student[],
  attendanceTypes: AttendanceType[],
  overwriteFilledInit: boolean,
  // Колбэки для синхронизации с родительским состоянием (буфер студентов)
  onBulkGrade: (field: GradeField, value: number | null) => void,
  onBulkAtt: (attId: number | null) => void,
  onClearAll: () => void
): UseBulkSheetReturn {
  const [overwriteFilled, setOverwriteFilled] = React.useState(overwriteFilledInit);
  const baselineRef = React.useRef<Student[]>([]);

  React.useEffect(() => {
    setOverwriteFilled(overwriteFilledInit);
  }, [overwriteFilledInit]);

  const firstEditable = (field: GradeField | 'attendance_type_id'): Student | undefined => {
    if (!overwriteFilled) {
      const e = students.find(s => {
        const base = baselineRef.current.find(b => b.id === s.id);
        return !base || base[field] == null;
      });
      if (e) return e;
    }
    return students[0];
  };

  const bulkSetGrade = (field: GradeField, value: number | null) => {
    onBulkGrade(field, value);
  };

  const bulkSetAtt = (attId: number | null) => {
    onBulkAtt(attId);
  };

  const clearAll = () => {
    onClearAll();
  };

  const resetBaseline = (newStudents: Student[]) => {
    baselineRef.current = newStudents.map(s => ({ ...s }));
  };

  return {
    overwriteFilled,
    setOverwriteFilled,
    baselineRef,
    firstEditable,
    bulkSetGrade,
    bulkSetAtt,
    clearAll,
    resetBaseline,
  };
}