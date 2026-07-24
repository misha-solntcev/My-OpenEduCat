export interface UserInfo {
  user_name: string;
  is_admin: boolean;
  is_teacher: boolean;
  is_student: boolean;
}

export interface AttendanceType {
  id: number;
  name: string;
}

export interface Student {
  id: number;
  name: string;
  avatar: string; // data:image/...;base64,... или '' (тогда показываем инициалы)
  grade_1: number | null;
  grade_2: number | null;
  grade_3: number | null;
  attendance_type_id: number | null;
}

// GradeField вывод из ключей Student
export type GradeField = 'grade_1' | 'grade_2' | 'grade_3';
export const GRADE_FIELDS: GradeField[] = ['grade_1', 'grade_2', 'grade_3'] as const;
export const GRADE_FIELD_LABELS: Record<GradeField, string> = {
  grade_1: 'О1',
  grade_2: 'О2',
  grade_3: 'О3',
};
