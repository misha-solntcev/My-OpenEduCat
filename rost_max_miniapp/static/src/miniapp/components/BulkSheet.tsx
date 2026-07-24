import React from 'react';
import { Flex, Avatar, Switch, IconButton, Button } from '@maxhub/max-ui';
import { Users, Eraser } from 'lucide-react';
import { GradeColumns } from '@/components/GradeColumns';
import type { Student, AttendanceType, GradeField } from '@/lib/types';

interface BulkSheetProps {
  students: Student[];
  attendanceTypes: AttendanceType[];
  overwriteFilled: boolean;
  onOverwriteFilledChange: (v: boolean) => void;
  // База цикла: первая релевантная строка (заполненная при !overwriteFilled,
  // иначе students[0]). Считается в родителе, т.к. зависит от baselineRef.
  firstEditable: (field: GradeField | 'attendance_type_id') => Student | undefined;
  onBulkGrade: (field: GradeField, value: number | null) => void;
  onBulkAtt: (attId: number | null) => void;
  onClearAll: () => void;
  onClose: () => void;
}

// Шторка массового проставления оценок/посещаемости всему классу.
// Кнопки — те же самодостаточные JournalButton (kind+value+onCycle),
// но onCycle пишет сразу всему классу через onBulkGrade/onBulkAtt.
export const BulkSheet: React.FC<BulkSheetProps> = ({
  attendanceTypes,
  overwriteFilled,
  onOverwriteFilledChange,
  firstEditable,
  onBulkGrade,
  onBulkAtt,
  onClearAll,
  onClose,
}) => (
  <div className="rm-bulk-sheet-overlay" onClick={onClose}>
    <div className="rm-bulk-sheet-card" onClick={e => e.stopPropagation()}>
      <Flex direction="column" gap={20}>
        {/* Режим массового выставления (Switch) + общий ластик — вверху
            справа отдельной строкой. Switch ВКЛ = перезаписать всех, ВЫКЛ =
            только уже проставленные строки (baseline != null).
            Ластик в том же визуальном языке, что Switch (IconButton). */}
        <Flex align="center" justify="end" gap={10} style={{ width: '100%' }}>
          <Switch
            checked={overwriteFilled}
            onChange={(e) => onOverwriteFilledChange(e.target.checked)}
            aria-label="Перезаписывать заполненные оценки"
          />
          <IconButton
            appearance="themed"
            mode="tertiary"
            onClick={onClearAll}
            title="Сбросить всё (оценки и посещаемость) у всего класса"
          >
            <Eraser size={20} />
          </IconButton>
        </Flex>

        {/* Сетка: аватар (SVG Users) + для каждой колонки (О1/О2/О3/Посещ)
            — кнопка-круг с tap-циклом (как на карточке ученика), но массово
            (пишет всему классу). */}
        <Flex align="flex-start" gap={6} wrap="nowrap" style={{ width: '100%', minWidth: 0 }}>
          <Avatar.Container size={44} form="squircle" className="rm-bulk-sheet-avatar" style={{ flexShrink: 0, marginTop: '0' }}>
            <Avatar.Icon>
              <Users size={20} color="var(--text-contrast-static)" />
            </Avatar.Icon>
          </Avatar.Container>

          <GradeColumns
            gradeValues={{
              grade_1: firstEditable('grade_1')?.grade_1 ?? null,
              grade_2: firstEditable('grade_2')?.grade_2 ?? null,
              grade_3: firstEditable('grade_3')?.grade_3 ?? null,
            }}
            onCycleGrade={(field, next) => onBulkGrade(field, next)}
            gradeVariant="bulk-grade"
            attendanceValue={firstEditable('attendance_type_id')?.attendance_type_id ?? null}
            onCycleAttendance={(next) => onBulkAtt(next)}
            attendanceVariant="bulk-attendance"
            attendanceTypes={attendanceTypes}
            gradeTitlePrefix="Оценка"
            attendanceTitle="Посещаемость — нажмите, чтобы сменить у всего класса"
          />
        </Flex>

        {/* Одна кнопка закрытия шторки. Массовые правки применяются к
            локальному буферу мгновенно, список за ширмой перерисовывается
            сразу. Сохранение на сервер — общей кнопкой «Сохранить». */}
        <Button
          stretched
          size="large"
          mode="primary"
          appearance="themed"
          onClick={onClose}
        >
          ОК
        </Button>
      </Flex>
    </div>
  </div>
);