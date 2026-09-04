import React from 'react';
import {
  AppRootPortal,
  ModalPage,
  ModalPageHeader,
  PanelHeaderClose,
  Button,
  ButtonGroup,
  Switch,
  Box,
  Flex,
  Text,
} from '@vkontakte/vkui';
import type { JournalColumns } from '@/shared/lib/types';

interface ColumnsSettingsSheetProps {
  columns: JournalColumns;
  onToggle: (key: 'grade_2' | 'grade_3' | 'note', value: boolean) => void;
  onClose: () => void;
  open: boolean;
}

interface ColumnRow {
  key: 'grade_2' | 'grade_3' | 'note' | null;
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
    { key: 'grade_3', title: 'Оценка 3', checked: columns.grade_3 },
    { key: null, title: 'Посещаемость', checked: true, locked: true },
    { key: 'note', title: 'Примечание', checked: columns.note },
  ];

  return (
    <AppRootPortal>
      <ModalPage
        open={open}
        onClose={onClose}
        header={
          <ModalPageHeader before={<PanelHeaderClose onClick={onClose} />}>
            Настройки
          </ModalPageHeader>
        }
        footer={
          <ButtonGroup gap="m" mode="vertical" stretched>
            <Button size="l" mode="primary" appearance="accent" onClick={onClose}>
              Готово
            </Button>
          </ButtonGroup>
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
