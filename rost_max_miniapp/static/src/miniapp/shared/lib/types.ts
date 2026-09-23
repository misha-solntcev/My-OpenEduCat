export interface UserInfo {
  user_name: string;
  /** URL своей аватарки ('' — рисуем инициалы). */
  avatar: string;
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
  /** Оценки за ДЗ — из строки сдачи задания урока (sub.line.marks/marks_2). */
  hw_grade_1: number | null;
  hw_grade_2: number | null;
  attendance_type_id: number | null;
  /** Примечание к строке (op.attendance.line.remark). Пусто — нет. */
  remark: string;
}

// GradeField вывод из ключей Student
export type GradeField = 'grade_1' | 'grade_2' | 'hw_grade_1' | 'hw_grade_2';

// --- API types (вынесены из страниц для единой точки правды) ---

export interface Lesson {
  id: number;
  subject: string;
  batch: string;
  timing: string;
  /** ФИО учителя */
  faculty: string;
  /** URL аватара учителя (/web/image). Пусто — нет фото или гость. */
  faculty_avatar?: string;
  /** Кабинет (op.classroom.name). Пусто — не задан. */
  room?: string;
  /** Состояние op.session (draft/done/cancel). */
  state?: string;
  /** id op.attendance.sheet (журнал). Есть только у teacher/admin. */
  sheet_id?: number | null;
}

export interface Faculty {
  id: number;
  name: string;
}

export interface Batch {
  id: number;
  name: string;
}

export interface TimetableResponse {
  lessons: Lesson[];
}

export interface FacultiesResponse {
  faculties: Faculty[];
}

export interface BatchesResponse {
  batches: Batch[];
}

// Журнал — типы ответов API для lesson journal
export interface LessonInfo {
  subject: string;
  batch: string;
  date: string;
  timing: string;
  can_edit?: boolean;
  /** Тема урока (op.attendance.sheet.lesson_topic). */
  topic: string;
  /** Домашнее задание (rost_lesson_homework.lesson_homework). */
  homework: string;
  /** id созданного op.assignment (задание по ДЗ). null — ДЗ не задано. */
  homework_assignment_id: number | null;
  /** «Требуется ответ при сдаче» (с задания или sheet). */
  homework_answer_required: boolean;
}

/** Персональная настройка колонок журнала. О1 и посещаемость всегда true. */
export interface JournalColumns {
  grade_1: boolean;
  grade_2: boolean;
  hw_grade_1: boolean;
  hw_grade_2: boolean;
  note: boolean;
  attendance: boolean;
}

export interface LessonJournalResponse {
  lesson: LessonInfo | null;
  students: Student[];
  attendance_types: AttendanceType[];
  columns?: JournalColumns;
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

// --- Лента дня (dashboard_info, вариант A) ---

export interface FeedLesson {
  id: number;
  sheet_id: number | null;
  subject: string;
  batch: string;
  faculty: string;
  /** Аватар учителя (путь к /web/image). Пусто — нет. */
  faculty_avatar?: string;
  timing: string;
  /** Кабинет (op.classroom.name). Пусто — не задан. */
  room?: string;
  start: string;
  end: string;
  is_now: boolean;
  journal_unfilled: boolean;
  homework: string;
}

export interface GradeToday {
  grades: number[];
  subject: string;
  comment: string;
}

export interface HomeworkItem {
  id: number;
  subject: string;
  /** Цвет предмета (Integer из op.subject, пастель web-календаря). 0 — не задан. */
  subject_color: number;
  /** Тема урока (op.attendance.sheet.lesson_topic журнала, создавшего задание). */
  topic: string;
  /** Дата выдачи (grading_assignment.issued_date). */
  issued_at: string;
  task: string;
  due: string;
  overdue: boolean;
  /** none | draft | submit | reject | change | accept */
  state: string;
  answer_required: boolean;
  answer: string;
  /** Оценка за сдачу (2–5). Не задана — null. */
  mark: number | null;
  /** Вторая оценка за сдачу (2–5). Не задана — null. */
  mark_2: number | null;
  teacher_note: string;
  submitted_at: string;
  late: boolean;
  /** Материалы задания (вложения учителя), одноразовые ссылки. */
  materials: HomeworkAttachment[];
}

export interface JournalToFill {
  sheet_id: number;
  subject: string;
  batch: string;
  timing: string;
  room: string;
  students: number;
}

export interface MyHomeworkItem {
  id: number;
  subject: string;
  batch: string;
  task: string;
  due: string;
  submitted: number;
  total: number;
  /** Сдач в состоянии submit (ждут проверки учителя). */
  to_review: number;
  answer_required: boolean;
  materials_count: number;
  /** Админ-лента: имя преподавателя для группировки по учителям. */
  faculty?: string;
}

export interface HomeworkAttachment {
  name: string;
  mimetype: string;
  /** Одноразовая ссылка /rost_max/hw_att/<token> (живёт 24 ч). */
  url: string;
}

export interface HomeworkSubmissionStudent {
  /** id строки сдачи op.assignment.sub.line — его ждёт /review в <sub_id>. */
  sub_id: number | null;
  student_id: number;
  name: string;
  /** none | draft | submit | reject | change | accept */
  state: string;
  answer: string;
  submitted_at: string;
  late: boolean;
  /** Оценка за сдачу (2–5). Не задана — null. */
  mark: number | null;
  /** Вторая оценка за сдачу (2–5). Не задана — null. */
  mark_2: number | null;
  teacher_note: string;
  attachments: HomeworkAttachment[];
  /** Фото ученика (/web/image/op.student/<id>/image_128); '' — нет фото. */
  avatar?: string;
  /** История сдачи из mail-трекинга (label — русская метка состояния). */
  history?: { date: string; label: string }[];
}

export interface HomeworkSubmissionsResponse {
  assignment: {
    id: number;
    subject: string;
    task: string;
    due: string;
    answer_required: boolean;
  };
  students: HomeworkSubmissionStudent[];
}

/** Элемент списка заданий учителя (GET /api/teacher_homework). */
export interface TeacherHomeworkItem {
  id: number;
  /** publish | finish */
  state: string;
  subject: string;
  /** Пастель квадрата предмета (op.subject.color, календарная палитра). */
  subject_color: number;
  batch: string;
  /** Тема урока (журнал, создавший задание). */
  topic: string;
  /** Дата выдачи (grading_assignment.issued_date). */
  issued_at: string;
  task: string;
  due: string;
  overdue: boolean;
  submitted: number;
  total: number;
  /** Сдач в состоянии submit (ждут проверки). */
  to_review: number;
  /** Принято (accept) — знаменатель прогресса проверки. */
  accepted: number;
  answer_required: boolean;
  materials_count: number;
  /** Журнал-источник (правка текста идёт через него); null — задание создано вне журнала. */
  sheet_id: number | null;
  /** Имя преподавателя (для админа; у учителя свои). */
  faculty: string;
}

export interface TeacherHomeworkResponse {
  homework: TeacherHomeworkItem[];
}

export interface AdminStats {
  lessons_today: number;
  batches_today: number;
  journals_unfilled: number;
}

export interface DashboardInfoResponse {
  is_admin: boolean;
  is_teacher: boolean;
  is_student: boolean;
  date: string;
  lessons: FeedLesson[];
  grades_today?: GradeToday[];
  homework?: HomeworkItem[];
  journals_to_fill?: JournalToFill[];
  my_homework?: MyHomeworkItem[];
  admin_stats?: AdminStats;
  alerts?: { kind: string; count: number; morning_passed: number }[];
  /** Учитель/админ: сводка ДЗ для табло (детали — на вкладке «Задания»). */
  hw_summary?: { to_review: number; issued: number; checked: number };
  metrics: Record<string, unknown>;
  next_lesson: unknown;
}

// --- Вкладка «Задания» (ученик/родитель) ---

export interface HomeworkListResponse {
  homework: HomeworkItem[];
}
