import React from 'react';
import { Flex, Avatar, Switch, IconButton, Button } from '@maxhub/max-ui';
import { Users, Eraser } from 'lucide-react';
import { JournalButton } from '@/components/JournalButton';
import { GRADE_FIELDS, GRADE_FIELD_LABELS, type GradeField } from '@/lib/colors';
import type { Student, AttendanceType } from '@/lib/types';

interface BulkSheetProps {
  students: Student[];
  attendanceTypes: AttendanceType[];
  overwriteAll: boolean;
  onOverwriteAllChange: (v: boolean) => void;
  // База цикла: первая релевантная строка (заполненная при !overwriteAll,
  // иначе students[0]). Считается в родителе, т.к. зависит от baselineRef.
  firstEditable: (field: GradeField | 'attendance_type_id') => Student | undefined;
  onBulkGrade: (field: GradeField, value: string) => void;
  onBulkAtt: (attId: number | null) => void;
  onClearAll: () => void;
  onClose: () => void;
}

// Шторка массового проставления оценок/посещаемости всему классу.
// Кнопки — те же самодостаточные JournalButton (kind+value+onCycle),
// но onCycle пишет сразу всему классу через onBulkGrade/onBulkAtt.
export const BulkSheet: React.FC<BulkSheetProps> = ({
  attendanceTypes,
  overwriteAll,
  onOverwriteAllChange,
  firstEditable,
  onBulkGrade,
  onBulkAtt,
  onClearAll,
  onClose,
}) => (
  <div
    onClick={onClose}
    style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(0,0,0,0.4)',
      zIndex: 100,
      display: 'flex',
      alignItems: 'flex-end',
    }}
  >
    <div
      onClick={e => e.stopPropagation()}
      style={{
        width: '100%',
        backgroundColor: 'var(--background-surface-card)',
        borderTopLeftRadius: '16px',
        borderTopRightRadius: '16px',
        padding: '20px 16px calc(20px + env(safe-area-inset-bottom))',
        boxSizing: 'border-box',
        animation: 'rm-sheet-up 0.2s ease-out',
      }}
    >
      <Flex direction="column" gap={20}>
        {/* Режим массового выставления (Switch) + общий ластик — вверху
            справа отдельной строкой. Switch ВКЛ = перезаписать всех, ВЫКЛ =
            только уже проставленные строки (baseline != null).
            Ластик в том же визуальном языке, что Switch (IconButton). */}
        <Flex align="center" justify="end" gap={10} style={{ width: '100%' }}>
          <Switch
            checked={overwriteAll}
            onChange={(e) => onOverwriteAllChange(e.target.checked)}
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
          <Avatar.Container size={44} form="squircle" className="rm-sheet-avatar" style={{ flexShrink: 0, marginTop: '0' }}>
            <Avatar.Icon>
              <Users size={20} color="var(--text-contrast-static)" />
            </Avatar.Icon>
          </Avatar.Container>

          {GRADE_FIELDS.map((gf) => (
            <JournalButton
              key={gf}
              kind="grade"
              value={firstEditable(gf)?.[gf] ?? null}
              onCycle={(next) => onBulkGrade(gf, next == null ? '' : String(next))}
              title={`Оценка ${GRADE_FIELD_LABELS[gf]} — нажмите, чтобы сменить у всего класса`}
              minWidth={38}
              height={40}
              padding="0 6px"
            />
          ))}

          <JournalButton
            kind="attendance"
            value={firstEditable('attendance_type_id')?.attendance_type_id ?? null}
            attendanceTypes={attendanceTypes}
            onCycle={(next) => onBulkAtt(next)}
            title="Посещаемость — нажмите, чтобы сменить у всего класса"
            fontSize={12}
            minWidth={34}
            height={40}
            padding="0 10px"
            whiteSpace="nowrap"
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
