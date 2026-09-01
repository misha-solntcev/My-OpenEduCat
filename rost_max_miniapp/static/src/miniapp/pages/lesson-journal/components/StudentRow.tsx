import React from 'react';
import { Flex, Avatar, EllipsisText, Box } from '@vkontakte/vkui';
import { GradeColumns } from './GradeColumns';
import { initialsOf } from '@/shared/lib/initials';
import type { Student, AttendanceType, GradeField } from '@/shared/lib/types';

interface StudentRowProps {
  student: Student;
  attendanceTypes: AttendanceType[];
  canEdit?: boolean;
  onCycleGrade?: (student: Student, field: GradeField, next: number | null) => void;
  onCycleAttendance?: (student: Student, next: number | null) => void;
}

export const StudentRow: React.FC<StudentRowProps> = ({
  student,
  attendanceTypes,
  canEdit = true,
  onCycleGrade,
  onCycleAttendance,
}) => (
  <Box padding="m">
    <Flex align="center" gap={12}>
      <Avatar
        size={40}
        initials={initialsOf(student.name)}
        src={student.avatar}
      />

      <Flex direction="column" gap={6} flexGrow={1} minInlineSize={0}>
        <EllipsisText maxLines={1}>
          {student.name}
        </EllipsisText>

        <GradeColumns
          gradeValues={{
            grade_1: student.grade_1,
            grade_2: student.grade_2,
            grade_3: student.grade_3,
          }}
          onCycleGrade={canEdit && onCycleGrade ? (field, next) => onCycleGrade(student, field, next) : undefined}
          gradeVariant="grade"
          attendanceValue={student.attendance_type_id}
          onCycleAttendance={canEdit && onCycleAttendance ? (next) => onCycleAttendance(student, next) : undefined}
          attendanceVariant="attendance"
          attendanceTypes={attendanceTypes}
        />
      </Flex>
    </Flex>
  </Box>
);