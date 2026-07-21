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
