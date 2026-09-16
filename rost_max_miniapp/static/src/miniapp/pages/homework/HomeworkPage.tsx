/**
 * Вкладка «Задания» (ученик/родитель): три блока — «Новые» (не сдано,
 * включая «на доработку» с комментарием учителя) / «Сдано» (ждёт
 * проверки) / «Проверено» (принято).
 */
import React from 'react';
import { Panel, Div, Spinner, Button, Placeholder, Caption, Title } from '@vkontakte/vkui';
import { Icon56DocumentOutline } from '@vkontakte/icons';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { HomeworkCardList } from '@/shared/components/HomeworkCardList';
import type { HomeworkItem, HomeworkListResponse } from '@/shared/lib/types';

interface HomeworkPageProps {
  id: string;
}

/** Заголовок группы заданий: крупный текст + цветная точка-статус +
 *  плашка-счётчик количества заданий в группе. Цвет несёт точка и
 *  счётчик (токены VKUI, без кастомных цветов); сам текст — text_primary
 *  (адаптивный, читается в обеих темах). */
const GroupTitle: React.FC<{ label: string; count: number; dot: string }> = ({ label, count, dot }) => (
  <Div style={{ paddingTop: 14, paddingBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
    <span style={{
      width: 10, height: 10, borderRadius: '50%', flexShrink: 0, background: dot,
    }} />
    <Title level="3" style={{ color: 'var(--vkui--color_text_primary)' }}>
      {label}
    </Title>
    <span style={{
      minWidth: 24, height: 22, borderRadius: 11, flexShrink: 0,
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      padding: '0 8px', fontSize: 13, fontWeight: 600,
      color: 'var(--vkui--color_text_primary)',
      background: 'var(--vkui--color_background_positive_tint)',
      border: '1px solid var(--vkui--color_stroke_positive)',
    }}>
      {count}
    </span>
  </Div>
);

/** Группировка по состоянию сдачи.
 *
 * Новые: ещё не сдано (none/draft), включая «на доработку» (change/reject)
 * с комментарием учителя — их нужно переделать и пересдать.
 * Сдано: submit, ждёт проверки. Проверено: принято.
 */
const groupHomework = (items: HomeworkItem[]): {
  fresh: HomeworkItem[];
  submitted: HomeworkItem[];
  checked: HomeworkItem[];
} => {
  const fresh: HomeworkItem[] = [];
  const submitted: HomeworkItem[] = [];
  const checked: HomeworkItem[] = [];
  for (const h of items) {
    if (h.state === 'accept') checked.push(h);
    else if (h.state === 'submit') submitted.push(h);
    else fresh.push(h);
  }
  return { fresh, submitted, checked };
};

export const HomeworkPage: React.FC<HomeworkPageProps> = ({ id }) => {
  const addToast = useToast();
  const [items, setItems] = React.useState<HomeworkItem[] | null>(null);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiGet<HomeworkListResponse>('/rost_max/api/homework');
      setItems(res.homework || []);
    } catch {
      addToast('Не удалось загрузить задания', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  React.useEffect(() => { load(); }, [load]);

  const submitHomework = async (
    assignmentId: number,
    answer: string,
    files: { filename: string; mimetype: string; b64: string }[],
  ): Promise<string | null> => {
    try {
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/submit`,
        { answer, files });
      if (res.error) {
        addToast(res.error, 'error');
        return res.error;
      }
      addToast('Домашнее задание сдано', 'success');
      return null;
    } catch {
      addToast('Не удалось сдать задание', 'error');
      return 'error';
    }
  };

  const submit = React.useCallback((
    id: number, answer: string,
    files: { filename: string; mimetype: string; b64: string }[],
  ) => submitHomework(id, answer, files), [addToast]);

  const groups = React.useMemo(
    () => groupHomework(items || []),
    [items],
  );

  return (
    <Panel id={id}>
      {/* Корневой таб: без PanelHeader — активный таб виден в таббаре */}
      {loading && !items ? (
        <Div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spinner size="l" />
        </Div>
      ) : !items ? (
        <Div>
          <Button mode="outline" stretched onClick={load}>Повторить</Button>
        </Div>
      ) : items.length === 0 ? (
        <Placeholder icon={<Icon56DocumentOutline />} title="Заданий нет">
          <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
            Новых домашних заданий не задано.
          </Caption>
        </Placeholder>
      ) : (
        <>
          {groups.fresh.length > 0 && (
            <HomeworkCardList
              items={groups.fresh}
              title={<GroupTitle label="Новые" count={groups.fresh.length} dot="var(--vkui--color_background_accent)" />}
              canSubmit
              onSubmit={submit}
              onUpdated={load}
            />
          )}
          {groups.submitted.length > 0 && (
            <HomeworkCardList
              items={groups.submitted}
              title={<GroupTitle label="Сдано" count={groups.submitted.length} dot="var(--vkui--color_icon_warning)" />}
              canSubmit={false}
              onUpdated={load}
            />
          )}
          {groups.checked.length > 0 && (
            <HomeworkCardList
              items={groups.checked}
              title={<GroupTitle label="Проверено" count={groups.checked.length} dot="var(--vkui--color_background_positive)" />}
              canSubmit={false}
              onUpdated={load}
            />
          )}
        </>
      )}
    </Panel>
  );
};
