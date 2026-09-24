/**
 * Шторка «Весь класс» в очереди проверки ДЗ — по образцу BulkSheet
 * журнала урока: шаблонные значения (оценка, комментарий) применяются
 * сразу всем ученикам задания, потом точечные правки в очереди.
 * Принять всем = accept у всех, у кого ещё нет accept (включая несдавших —
 * приём без сдачи); тумблер «Перезаписывать» — пере-принять уже принятых.
 */
import React from 'react';
import {
  Flex, Switch, ModalPage, ModalPageHeader, PanelHeaderClose,
  Button, IconButton, AppRootPortal, Box, Alert,
  Caption, Input,
} from '@vkontakte/vkui';
import { Icon28ArrowUpRightOutSquareOutline, Icon28DeleteOutline } from '@vkontakte/icons';
import { JournalButton } from '@/shared/components/JournalButton';
import { apiPost } from '@/shared/lib/api';

interface BulkReviewSheetProps {
  assignmentId: number;
  open: boolean;
  onClose: () => void;
  /** Вызывается после успешного массового приёма (перезагрузить очередь). */
  onApplied: () => void;
  onError: (message: string) => void;
}

export const BulkReviewSheet: React.FC<BulkReviewSheetProps> = ({
  assignmentId, open, onClose, onApplied, onError,
}) => {
  // Локальные шаблоны шторки (UI-only): сбрасываются при открытии.
  const [mark, setMark] = React.useState<number | null>(null);
  const [mark2, setMark2] = React.useState<number | null>(null);
  const [note, setNote] = React.useState('');
  const [overwrite, setOverwrite] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [confirmClear, setConfirmClear] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setMark(null);
      setMark2(null);
      setNote('');
      setOverwrite(false);
      setConfirmClear(false);
    }
  }, [open]);

  const clearAll = async () => {
    if (busy) return;
    setConfirmClear(false);
    setBusy(true);
    try {
      const res = await apiPost<{ success?: boolean; updated?: number; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/review_bulk`,
        { clear: true });
      if (res.error) {
        onError(res.error);
      } else {
        onApplied();
        onClose();
        return;
      }
    } catch {
      onError('Не удалось очистить оценки у всего класса');
    } finally {
      setBusy(false);
    }
  };

  const applyAll = async () => {
    setBusy(true);
    try {
      const res = await apiPost<{ success?: boolean; updated?: number; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/review_bulk`,
        { mark: mark ?? '', mark_2: mark2 ?? '', overwrite, teacher_note: note.trim() });
      if (res.error) {
        onError(res.error);
      } else {
        onApplied();
        onClose();
        return;
      }
    } catch {
      onError('Не удалось применить ко всему классу');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppRootPortal usePortal>
      <ModalPage
        open={open}
        onClose={onClose}
        header={
          <ModalPageHeader
            before={<PanelHeaderClose onClick={onClose} />}
            after={
              <Flex align="center" gap={8}>
                <Switch
                  checked={overwrite}
                  disabled={busy}
                  onChange={e => setOverwrite(e.target.checked)}
                  aria-label="Перезаписывать уже принятых"
                />
                <IconButton
                  label="Очистить оценки и комментарий у всего класса"
                  disabled={busy}
                  onClick={e => {
                    e.stopPropagation();
                    setConfirmClear(true);
                  }}
                >
                  <Icon28DeleteOutline />
                </IconButton>
              </Flex>
            }
          >
            Весь класс
          </ModalPageHeader>
        }
      >
        <Box padding="m" paddingInline="l" paddingBlockEnd="xl">
          <Flex direction="column" gap={16}>
            {/* Оценка всем — кнопка журнала (цикл — → 5 → 4 → 3 → 2 → —).
                «—» = принять без оценки; существующие оценки не трогаем. */}
            <Flex align="center" gap={10}>
              <JournalButton
                kind="grade"
                value={mark}
                onCycle={setMark}
                title="Оценка 1 всему классу"
              />
              <JournalButton
                kind="grade"
                value={mark2}
                onCycle={setMark2}
                title="Оценка 2 всему классу"
              />
              <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Оценки всем («—» — принять без оценки)
              </Caption>
            </Flex>

            <Flex direction="column" gap={4}>
              <Caption level="1" style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Комментарий всем
              </Caption>
              <Input
                value={note}
                onChange={e => setNote(e.target.value)}
                placeholder="Например: Молодцы, все справились"
                aria-label="Комментарий всему классу"
              />
            </Flex>

            {/* Кнопка действия — в теле шторки, НЕ в футере ModalPage:
                в MAX WebView футер может не показываться (как «ОК» в журнале). */}
            <Button
              size="l" mode="primary" appearance="accent" stretched
              loading={busy} disabled={confirmClear} onClick={applyAll}
            >
              Принять у всех
            </Button>

            <Flex align="center" gap={6}>
              <Icon28ArrowUpRightOutSquareOutline width={16} height={16}
                style={{ color: 'var(--vkui--color_text_secondary)', flexShrink: 0 }} />
              <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Принимает и тех, кто не сдал (ответ был устно или в тетради).
                Тумблер сверху — перезаписать уже принятых.
              </Caption>
            </Flex>
          </Flex>
        </Box>
      </ModalPage>
      {confirmClear && (
        <Alert
          onClose={() => setConfirmClear(false)}
          onClosed={() => setConfirmClear(false)}
          title="Очистить у всего класса?"
          description="Оценки и комментарии учителя будут удалены без возможности восстановления. Состояние сдач при этом не изменится."
          actions={[
            { title: 'Отмена', mode: 'cancel' },
            { title: 'Очистить', mode: 'destructive', action: clearAll },
          ]}
        />
      )}
    </AppRootPortal>
  );
};
