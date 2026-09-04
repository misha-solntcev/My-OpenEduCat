import React from 'react';
import { Flex, Avatar, Switch, IconButton, ModalPage, ModalPageHeader, PanelHeaderClose, Button, ButtonGroup, unstable_ModalPageFooter as ModalPageFooter, AppRootPortal, Box } from '@vkontakte/vkui';
import { Icon28DeleteOutline } from '@vkontakte/icons';
import { GradeColumns } from './GradeColumns';
import type { AttendanceType, GradeField, JournalColumns } from '@/shared/lib/types';

interface BulkSheetProps {
  attendanceTypes: AttendanceType[];
  overwriteFilled: boolean;
  onOverwriteFilledChange: (v: boolean) => void;
  onBulkGrade: (field: GradeField, value: number | null) => void;
  onBulkAtt: (attId: number | null) => void;
  onClearAll: () => void;
  onClose: () => void;
  open: boolean;
  /** Персональная настройка колонок: скрытая О2/О3 недоступна и в шторке. */
  columns?: JournalColumns;
}

// Шторка массового проставления оценок/посещаемости всему классу.
// Использует нативный VKUI v8+ ModalPage — на мобильных: нижняя шторка (Bottom Sheet), на десктопе: диалог.
export const BulkSheet: React.FC<BulkSheetProps> = ({
  attendanceTypes,
  overwriteFilled,
  onOverwriteFilledChange,
  onBulkGrade,
  onBulkAtt,
  onClearAll,
  onClose,
  open,
  columns,
}) => {
  // Локальное состояние шаблонных значений для кнопок в шторке (UI-only)
  const [bulkGradeValues, setBulkGradeValues] = React.useState<Record<GradeField, number | null>>({
    grade_1: null,
    grade_2: null,
    grade_3: null,
  });
  const [bulkAttendanceValue, setBulkAttendanceValue] = React.useState<number | null>(null);

  // Сбросить локальные шаблоны при открытии шторки
  React.useEffect(() => {
    setBulkGradeValues({ grade_1: null, grade_2: null, grade_3: null });
    setBulkAttendanceValue(null);
  }, [open]);

  return (
    <AppRootPortal>
      <ModalPage
        open={open}
        onClose={onClose}
        header={
          <ModalPageHeader
            before={<PanelHeaderClose onClick={onClose} />}
          >
            Массовая расстановка
          </ModalPageHeader>
        }
        footer={
          <ModalPageFooter>
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
          </ModalPageFooter>
        }
      >
        {/* Отступы внутри ModalPage задаются через контентный блок */}
        <Box padding="m" paddingInline="l" paddingBlockEnd="xl">
          <Flex direction="column" gap={20}>

            {/* Панель настроек (Свитч перезаписи и Ластик) */}
            <Flex align="center" justify="end" gap={10} inlineSize="100%">
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

            {/* Интерактивная строка ввода для всего класса */}
            <Flex align="start" gap={6} wrap="nowrap" inlineSize="100%" minInlineSize={0}>
              <Avatar size={44} initials="👥" gradientColor="blue" flexShrink={0} />

              <GradeColumns
                gradeValues={bulkGradeValues}
                onCycleGrade={(field, next) => { onBulkGrade(field, next); setBulkGradeValues(p => ({ ...p, [field]: next })); }}
                gradeVariant="bulk-grade"
                attendanceValue={bulkAttendanceValue}
                onCycleAttendance={(next) => { onBulkAtt(next); setBulkAttendanceValue(next); }}
                attendanceVariant="bulk-attendance"
                attendanceTypes={attendanceTypes}
                gradeTitlePrefix="Оценка"
                attendanceTitle="Посещаемость — нажмите, чтобы сменить у всего класса"
                columns={columns}
              />
            </Flex>
          </Flex>
        </Box>
      </ModalPage>
    </AppRootPortal>
  );
};