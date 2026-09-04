import React from 'react';
import { Flex, Avatar, Switch, IconButton, ModalPage, ModalPageHeader, PanelHeaderClose, Button, ButtonGroup, unstable_ModalPageFooter as ModalPageFooter, AppRootPortal, Box, Caption, Input } from '@vkontakte/vkui';
import { Icon28DeleteOutline } from '@vkontakte/icons';
import { GradeColumns } from './GradeColumns';
import type { AttendanceType, GradeField, JournalColumns } from '@/shared/lib/types';

interface BulkSheetProps {
  attendanceTypes: AttendanceType[];
  overwriteFilled: boolean;
  onOverwriteFilledChange: (v: boolean) => void;
  onBulkGrade: (field: GradeField, value: number | null) => void;
  onBulkAtt: (attId: number | null) => void;
  onBulkRemark: (remark: string) => void;
  onClearAll: () => void;
  onClose: () => void;
  open: boolean;
  /** Персональная настройка колонок: скрытые О2/О3/примечание недоступны и в шторке. */
  columns?: JournalColumns;
}

// Шторка «Весь класс»: проставление оценок/посещаемости/примечания сразу
// всем ученикам. Тумблер перезаписи и корзина — в заголовке.
export const BulkSheet: React.FC<BulkSheetProps> = ({
  attendanceTypes,
  overwriteFilled,
  onOverwriteFilledChange,
  onBulkGrade,
  onBulkAtt,
  onBulkRemark,
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
  const [bulkRemark, setBulkRemark] = React.useState('');

  // Сбросить локальные шаблоны при открытии шторки
  React.useEffect(() => {
    setBulkGradeValues({ grade_1: null, grade_2: null, grade_3: null });
    setBulkAttendanceValue(null);
    setBulkRemark('');
  }, [open]);

  const showNote = Boolean(columns?.note);

  return (
    <AppRootPortal>
      <ModalPage
        open={open}
        onClose={onClose}
        header={
          <ModalPageHeader
            before={<PanelHeaderClose onClick={onClose} />}
            after={
              <Flex align="center" gap={8}>
                <Switch
                  checked={overwriteFilled}
                  onChange={e => onOverwriteFilledChange(e.target.checked)}
                  aria-label="Перезаписывать заполненное"
                />
                <IconButton
                  label="Сбросить всё (оценки, посещаемость, примечания) у всего класса"
                  onClick={e => { e.stopPropagation(); onClearAll(); }}
                >
                  <Icon28DeleteOutline />
                </IconButton>
              </Flex>
            }
          >
            Весь класс
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
                Готово
              </Button>
            </ButtonGroup>
          </ModalPageFooter>
        }
      >
        <Box padding="m" paddingInline="l" paddingBlockEnd="xl">
          <Flex direction="column" gap={16}>

            {/* Интерактивная строка ввода для всего класса */}
            <Flex align="start" gap={10} wrap="nowrap" inlineSize="100%" minInlineSize={0}>
              <Avatar size={44} initials="👥" gradientColor="blue" style={{ flexShrink: 0 }} />

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

            {/* Примечание всему классу — только если колонка включена в настройках */}
            {showNote && (
              <Flex direction="column" gap={4}>
                <Caption level="1" style={{ color: 'var(--vkui--color_text_secondary)' }}>
                  Примечание всем
                </Caption>
                <Input
                  value={bulkRemark}
                  onChange={e => setBulkRemark(e.target.value)}
                  onBlur={() => onBulkRemark(bulkRemark.trim())}
                  placeholder="Например: Готовимся к контрольной"
                  aria-label="Примечание всему классу"
                />
              </Flex>
            )}
          </Flex>
        </Box>
      </ModalPage>
    </AppRootPortal>
  );
};
