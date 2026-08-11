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

// --- API types (вынесены из страниц для единой точки правды) ---

export interface Lesson {
  id: number;
  subject: string;
  batch: string;
  timing: string;
  faculty: string;
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
  id: number;
  subject: string;
  batch: string;
  timing: string;
  date: string;
}

export interface LessonJournalResponse {
  lesson: LessonInfo;
  students: Student[];
  attendance_types: AttendanceType[];
  // grade_1, grade_2, grade_3 — числа 1-5 или null
  // attendance_type_id — id из attendance_types или null
}

// Dashboard API response
export interface DashboardMetrics {
  active_lessons?: number;
  unfilled_sheets?: number;
  attendance_pct?: number;
  total_students?: number;
  pending_substitutes?: number;
  total_lessons?: number;
  completed_lessons?: number;
  graded_count?: number;
  gpa?: number;
  pending_homework?: number;
}

export interface NextLesson {
  id: number;
  subject: string;
  batch: string;
  time: string;
  room: string;
}

export interface DashboardResponse {
  is_admin: boolean;
  is_teacher: boolean;
  is_student: boolean;
  date: string;
  metrics: DashboardMetrics;
  next_lesson: NextLesson | null;
}
