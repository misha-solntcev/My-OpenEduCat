import React from 'react';
import { Box, Flex, Avatar, EllipsisText } from '@vkontakte/vkui';
import { GradeColumns } from '@/components/GradeColumns';
import { initialsOf } from '@/lib';
import type { Student, AttendanceType, GradeField } from '@/lib/types';

interface StudentRowProps {
  student: Student;
  attendanceTypes: AttendanceType[];
  onCycleGrade: (student: Student, field: GradeField, next: number | null) => void;
  onCycleAttendance: (student: Student, next: number | null) => void;
}

export const StudentRow: React.FC<StudentRowProps> = ({
  student,
  attendanceTypes,
  onCycleGrade,
  onCycleAttendance,
}) => (
  <Box mode="card" padding="m">
    <Flex align="center" gap={12}>
      <Avatar
        size={40}
        initials={initialsOf(student.name)}
        src={student.avatar}
      />

      <Flex direction="column" gap={6} style={{ flex: 1, minWidth: 0 }}>
        <EllipsisText maxLines={1}>
          {student.name}
        </EllipsisText>

        <GradeColumns
          gradeValues={{
            grade_1: student.grade_1,
            grade_2: student.grade_2,
            grade_3: student.grade_3,
          }}
          onCycleGrade={(field, next) => onCycleGrade(student, field, next)}
          gradeVariant="grade"
          attendanceValue={student.attendance_type_id}
          onCycleAttendance={(next) => onCycleAttendance(student, next)}
          attendanceVariant="attendance"
          attendanceTypes={attendanceTypes}
        />
      </Flex>
    </Flex>
  </Box>
);