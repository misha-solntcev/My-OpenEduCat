import React from 'react';
import { Flex, Avatar, EllipsisText, Box, Input } from '@vkontakte/vkui';
import { GradeColumns } from './GradeColumns';
import { initialsOf } from '@/shared/lib/initials';
import type { Student, AttendanceType, GradeField, JournalColumns } from '@/shared/lib/types';

interface StudentRowProps {
  student: Student;
  attendanceTypes: AttendanceType[];
  canEdit?: boolean;
  columns: JournalColumns;
  onCycleGrade?: (student: Student, field: GradeField, next: number | null) => void;
  onCycleAttendance?: (student: Student, next: number | null) => void;
  onRemarkChange?: (student: Student, remark: string) => void;
}

/** Пункт.меню-подобный ввод примечания: компактное поле под кнопками. */
const RemarkInput: React.FC<{
  value: string;
  onChange: (v: string) => void;
}> = ({ value, onChange }) => (
  <Input
    value={value}
    onChange={e => onChange(e.target.value)}
    placeholder="Примечание"
    aria-label="Примечание"
    style={{ marginTop: 8 }}
  />
);

export const StudentRow: React.FC<StudentRowProps> = ({
  student,
  attendanceTypes,
  canEdit = true,
  columns,
  onCycleGrade,
  onCycleAttendance,
  onRemarkChange,
}) => (
  <Box padding="m">
    <Flex align="center" gap={12}>
      {/* Как учителя в расписании: без /WxH на бэкенде, квадрат режет браузер
          через objectPosition='center top' (иначе серверный кроп срезает лоб). */}
      <Avatar
        size={40}
        initials={initialsOf(student.name)}
        src={student.avatar || undefined}
        objectPosition="center top"
        style={{ borderRadius: 8, flexShrink: 0 }}
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
          columns={columns}
        />

        {canEdit && columns.note && onRemarkChange && (
          <RemarkInput
            value={student.remark || ''}
            onChange={v => onRemarkChange(student, v)}
          />
        )}
        {!canEdit && columns.note && student.remark && (
          <EllipsisText maxLines={2} style={{ color: 'var(--vkui--color_text_secondary)' }}>
            {student.remark}
          </EllipsisText>
        )}
      </Flex>
    </Flex>
  </Box>
);
