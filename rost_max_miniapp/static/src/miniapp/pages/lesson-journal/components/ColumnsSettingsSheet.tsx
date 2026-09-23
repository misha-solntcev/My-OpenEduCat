import React from 'react';
import {
  AppRootPortal,
  ModalPage,
  ModalPageHeader,
  PanelHeaderClose,
  Button,
  Switch,
  Box,
  Flex,
  Text,
} from '@vkontakte/vkui';
import type { JournalColumns } from '@/shared/lib/types';

interface ColumnsSettingsSheetProps {
  columns: JournalColumns;
  onToggle: (key: 'grade_2' | 'hw_grade_1' | 'hw_grade_2' | 'note', value: boolean) => void;
  onClose: () => void;
  open: boolean;
}

interface ColumnRow {
  key: 'grade_2' | 'hw_grade_1' | 'hw_grade_2' | 'note' | null;
  title: string;
  checked: boolean;
  locked?: boolean;
}

/** Шторка «Настройки» журнала (вариант B: шестерёнка → ModalPage). */
export const ColumnsSettingsSheet: React.FC<ColumnsSettingsSheetProps> = ({
  columns,
  onToggle,
  onClose,
  open,
}) => {
  // О1 и посещаемость включены всегда, переключатели остальных идут на сервер.
  const rows: ColumnRow[] = [
    { key: null, title: 'Оценка 1', checked: true, locked: true },
    { key: 'grade_2', title: 'Оценка 2', checked: columns.grade_2 },
    { key: 'hw_grade_1', title: 'ДЗ 1', checked: columns.hw_grade_1 },
    { key: 'hw_grade_2', title: 'ДЗ 2', checked: columns.hw_grade_2 },
    { key: null, title: 'Посещаемость', checked: true, locked: true },
    { key: 'note', title: 'Примечание', checked: columns.note },
  ];

  return (
    <AppRootPortal usePortal>
      <ModalPage
        open={open}
        onClose={onClose}
        header={
          <ModalPageHeader before={<PanelHeaderClose onClick={onClose} />}>
            Настройки
          </ModalPageHeader>
        }
        footer={
          <Flex justify="center">
            <Button size="l" mode="primary" appearance="accent" onClick={onClose}>
              ОК
            </Button>
          </Flex>
        }
      >
        <Box padding="m" paddingInline="l" paddingBlockEnd="xl">
          <Flex direction="column" style={{ marginTop: 8 }}>
            {rows.map(row => (
              <Flex key={row.title} align="center" gap={12} style={{ paddingBlock: 10 }}>
                <Flex direction="column" style={{ flexGrow: 1, minWidth: 0 }}>
                  <Text weight="2">{row.title}</Text>
                </Flex>
                <Switch
                  checked={row.checked}
                  disabled={row.locked}
                  onChange={e => row.key && onToggle(row.key, e.target.checked)}
                  aria-label={row.title}
                />
              </Flex>
            ))}
          </Flex>
        </Box>
      </ModalPage>
    </AppRootPortal>
  );
};
