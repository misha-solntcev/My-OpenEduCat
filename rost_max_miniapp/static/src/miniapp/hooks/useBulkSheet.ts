import React from 'react';
import type { Student, AttendanceType, GradeField } from '@/lib/types';

interface UseBulkSheetReturn {
  overwriteFilled: boolean;
  setOverwriteFilled: (v: boolean) => void;
  baselineRef: React.MutableRefObject<Student[]>;
  bulkSetGrade: (field: GradeField, value: number | null) => void;
  bulkSetAtt: (attId: number | null) => void;
  clearAll: () => void;
  resetBaseline: (students: Student[]) => void;
}

export function useBulkSheet(
  _students: Student[],
  _attendanceTypes: AttendanceType[],
  overwriteFilledInit: boolean,
  onBulkGrade: (field: GradeField, value: number | null) => void,
  onBulkAtt: (attId: number | null) => void,
  onClearAll: () => void
): UseBulkSheetReturn {
  const [overwriteFilled, setOverwriteFilled] = React.useState(overwriteFilledInit);
  const baselineRef = React.useRef<Student[]>([]);

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