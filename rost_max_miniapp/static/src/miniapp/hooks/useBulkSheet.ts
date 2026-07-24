import React from 'react';
import type { Student, AttendanceType } from '@/lib/types';
import type { GradeField } from '@/lib/colors';

interface UseBulkSheetReturn {
  overwriteFilled: boolean;
  setOverwriteFilled: (v: boolean) => void;
  baselineRef: React.MutableRefObject<Student[]>;
  bulkSetGrade: (field: GradeField, value: number | null) => void;
  bulkSetAtt: (attId: number | null) => void;
  clearAll: () => void;
  resetBaseline: (students: Student[]) => void;
}

/**
 * Хук логики массовой шторки (BulkSheet):
 * - overwriteFilled (перезаписывать заполненные / только пустые)
 * - baselineRef (снимок студентов на момент открытия шторки)
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
  onClearAll: (students: Student[]) => void
): UseBulkSheetReturn {
  const [overwriteFilled, setOverwriteFilled] = React.useState(overwriteFilledInit);
  const baselineRef = React.useRef<Student[]>([]);

  React.useEffect(() => {
    setOverwriteFilled(overwriteFilledInit);
  }, [overwriteFilledInit]);

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
    bulkSetGrade,
    bulkSetAtt,
    clearAll,
    resetBaseline,
  };
}