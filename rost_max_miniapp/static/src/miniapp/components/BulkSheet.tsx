import { Flex, Avatar, Switch, IconButton, Button, ModalCard, ButtonGroup } from '@vkontakte/vkui';
import { Icon28DeleteOutline } from '@vkontakte/icons';
import { GradeColumns } from '@/components/GradeColumns';
import type { AttendanceType, GradeField } from '@/lib/types';

interface BulkSheetProps {
  attendanceTypes: AttendanceType[];
  overwriteFilled: boolean;
  onOverwriteFilledChange: (v: boolean) => void;
  onBulkGrade: (field: GradeField, value: number | null) => void;
  onBulkAtt: (attId: number | null) => void;
  onClearAll: () => void;
  onClose: () => void;
  open: boolean;
}

// Шторка массового проставления оценок/посещаемости всему классу.
// Использует VKUI ModalCard вместо кастомного overlay + CSS-классов.
export const BulkSheet: React.FC<BulkSheetProps> = ({
  attendanceTypes,
  overwriteFilled,
  onOverwriteFilledChange,
  onBulkGrade,
  onBulkAtt,
  onClearAll,
  onClose,
  open,
}) => {
  if (!open) return null;

  return (
    <ModalCard
      open={open}
      onClose={onClose}
      title="Массовая расстановка"
      dismissLabel="Закрыть"
      size={400}
      actions={
        <ButtonGroup gap="m" mode="vertical" stretched>
          <Button
            size="l"
            mode="primary"
            appearance="accent"
            onClick={onClose}
          >
            ОК
          </Button>
        </ButtonGroup>
      }
    >
      <Flex direction="column" gap={20}>
        {/* Режим массового выставления (Switch) + общий ластик — вверху справа отдельной строкой. */}
        <Flex align="center" justify="end" gap={10}>
          <Switch
            checked={overwriteFilled}
            onChange={e => onOverwriteFilledChange(e.target.checked)}
            aria-label="Перезаписывать заполненные оценки"
          />
          <IconButton
            label="Сбросить всё (оценки и посещаемость) у всего класса"
            onClick={e => { e.stopPropagation(); onClearAll(); }}
          >
            <Icon28DeleteOutline />
          </IconButton>
        </Flex>

        {/* Сетка: аватар (SVG Users) + для каждой колонки (О1/О2/О3/Посещ)
            — кнопка-круг с tap-циклом (как на карточке ученика), но массово
            (пишет всему классу). */}
        <Flex align="start" gap={6} wrap="nowrap">
          <Avatar size={44} initials="👥" gradientColor="blue" />

          <GradeColumns
            gradeValues={{
              grade_1: null,
              grade_2: null,
              grade_3: null,
            }}
            onCycleGrade={(field, next) => onBulkGrade(field, next)}
            gradeVariant="bulk-grade"
            attendanceValue={null}
            onCycleAttendance={(next) => onBulkAtt(next)}
            attendanceVariant="bulk-attendance"
            attendanceTypes={attendanceTypes}
            gradeTitlePrefix="Оценка"
            attendanceTitle="Посещаемость — нажмите, чтобы сменить у всего класса"
          />
        </Flex>
      </Flex>
    </ModalCard>
  );
};