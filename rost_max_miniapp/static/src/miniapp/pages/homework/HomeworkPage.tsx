/**
 * Вкладка «Задания» (ученик/родитель): группы «Срочно сдать / На этой
 * неделе / Проверенные». Статусы итерации 1: Задано/Сдано/Просрочено.
 */
import React from 'react';
import { Panel, Div, Spinner, Button, Placeholder, Caption } from '@vkontakte/vkui';
import { Icon56DocumentOutline } from '@vkontakte/icons';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { HomeworkCardList } from '@/shared/components/HomeworkCardList';
import { schoolTodayISO } from '@/shared/lib/date';
import type { HomeworkItem, HomeworkListResponse } from '@/shared/lib/types';

interface HomeworkPageProps {
  id: string;
}

/** Серый подзаголовок группы заданий. */
const GroupTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Div style={{ paddingTop: 12, paddingBottom: 0 }}>
    <Caption style={{ color: 'var(--vkui--color_text_secondary)', fontWeight: 600 }}>
      {children}
    </Caption>
  </Div>
);

/** Парсер 'YYYY-MM-DD[ HH:MM[:SS]]' -> timestamp (без Date.parse и зон). */
const dueTs = (due: string): number => {
  const m = (due || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return NaN;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 23, 59, 59).getTime();
};

/** Школьная дата 'YYYY-MM-DD' как upper bound «просрочено» (конец дня). */
const dueTsOfToday = (): number => dueTs(schoolTodayISO() + ' 00:00:00');

/** Группировка по срочности (утверждённые группы итерации 1).
 *
 * Срочно сдать: просроченные, дедлайн в ближайшие 3 дня и «на доработку».
 * На этой неделе: всё остальное ещё не сданное. Проверенные: сдано/
 * принято.
 */
const groupHomework = (items: HomeworkItem[]): {
  urgent: HomeworkItem[];
  week: HomeworkItem[];
  checked: HomeworkItem[];
} => {
  const todayEnd = dueTsOfToday();
  const in3days = todayEnd + 2 * 86400_000;
  const urgent: HomeworkItem[] = [];
  const week: HomeworkItem[] = [];
  const checked: HomeworkItem[] = [];
  for (const h of items) {
    if (h.state === 'submit' || h.state === 'accept') {
      checked.push(h);
      continue;
    }
    const ts = dueTs(h.due);
    const urgentHit = h.overdue || h.state === 'change' || h.state === 'reject'
      || (isNaN(ts) ? true : ts <= in3days);
    if (urgentHit) urgent.push(h);
    else week.push(h);
  }
  return { urgent, week, checked };
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
          {groups.urgent.length > 0 && (
            <HomeworkCardList
              items={groups.urgent}
              title={<GroupTitle>Срочно сдать · {groups.urgent.length}</GroupTitle>}
              canSubmit
              onSubmit={submit}
              onUpdated={load}
            />
          )}
          {groups.week.length > 0 && (
            <HomeworkCardList
              items={groups.week}
              title={<GroupTitle>На этой неделе · {groups.week.length}</GroupTitle>}
              canSubmit
              onSubmit={submit}
              onUpdated={load}
            />
          )}
          {groups.checked.length > 0 && (
            <HomeworkCardList
              items={groups.checked}
              title={<GroupTitle>Проверенные · {groups.checked.length}</GroupTitle>}
              canSubmit={false}
              onUpdated={load}
            />
          )}
          <Div>
            <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
              Всего заданий: {items.length}
            </Caption>
          </Div>
        </>
      )}
    </Panel>
  );
};
