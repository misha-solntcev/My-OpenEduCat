export interface UserInfo {
  user_name: string;
  is_admin: boolean;
  is_teacher: boolean;
  is_student: boolean;
  is_parent?: boolean;
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

// --- API types (вынесены из страниц для единой точки правды) ---

export interface Lesson {
  id: number;
  subject: string;
  batch: string;
  timing: string;
  faculty: string;
  /** id op.attendance.sheet (журнал). Есть только у teacher/admin. */
  sheet_id?: number | null;
}

export interface Faculty {
  id: number;
  name: string;
}

export interface TimetableResponse {
  lessons: Lesson[];
}

export interface FacultiesResponse {
  faculties: Faculty[];
}

// Журнал — типы ответов API для lesson journal
export interface LessonInfo {
  subject: string;
  batch: string;
  date: string;
  timing: string;
  can_edit?: boolean;
}

export interface LessonJournalResponse {
  lesson: LessonInfo | null;
  students: Student[];
  attendance_types: AttendanceType[];
}

// --- Успеваемость (ученик / родитель, read-only) ---

export interface SubjectSummary {
  subject_id: number;
  name: string;
  average_mark: number;
  attendance_rate: number;
  total_classes: number;
  present_classes: number;
  last_remark: string;
  counts: Record<string, number>;
}

export interface StudentSubjects {
  student_id: number;
  name: string;
  subjects: SubjectSummary[];
}

export interface MySubjectsResponse {
  quarter: number;
  current_quarter: number;
  quarters: { q: number; name: string }[];
  students: StudentSubjects[];
}

export interface GradeLine {
  line_id: number;
  date: string;
  subject_id: number | null;
  subject: string;
  grades: number[];
  attendance_type_id: number | null;
  attendance: string | null;
  remark: string;
  topic: string;
}

export interface MyGradesResponse {
  quarter: number;
  subject_id: number;
  summary: {
    average_mark: number;
    attendance_rate: number;
    total_classes: number;
    present_classes: number;
    counts: Record<string, number>;
    last_remark: string;
  };
  lines: GradeLine[];
}
