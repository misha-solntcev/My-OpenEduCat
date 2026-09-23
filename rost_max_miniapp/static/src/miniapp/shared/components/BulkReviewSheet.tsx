/**
 * Шторка «Весь класс» в очереди проверки ДЗ — по образцу BulkSheet
 * журнала урока: шаблонные значения (оценка, комментарий) применяются
 * сразу всем ученикам задания, потом точечные правки в очереди.
 * Принять всем = accept у всех, у кого ещё нет accept (включая несдавших —
 * приём без сдачи); тумблер «Перезаписывать» — пере-принять уже принятых.
 */
import React from 'react';
import {
  Flex, Switch, IconButton, ModalPage, ModalPageHeader, PanelHeaderClose,
  Button, AppRootPortal, Box,
  Caption, Input,
} from '@vkontakte/vkui';
import { Icon28ArrowUpRightOutSquareOutline } from '@vkontakte/icons';
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
  const [note, setNote] = React.useState('');
  const [overwrite, setOverwrite] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setMark(null);
      setNote('');
      setOverwrite(false);
    }
  }, [open]);

  const applyAll = async () => {
    setBusy(true);
    try {
      const res = await apiPost<{ success?: boolean; updated?: number; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/review_bulk`,
        { mark: mark ?? '', overwrite, teacher_note: note.trim() });
      if (res.error) {
        onError(res.error);
      } else {
        onApplied();
        onClose();
        return;
      }
    } catch {
      onError('Не удалось применить ко всему классу');
    }
    setBusy(false);
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
              <Switch
                checked={overwrite}
                onChange={e => setOverwrite(e.target.checked)}
                aria-label="Перезаписывать уже принятых"
              />
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
                title="Оценка всему классу"
              />
              <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Оценка всем («—» — принять без оценки)
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
              loading={busy} onClick={applyAll}
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
    </AppRootPortal>
  );
};
