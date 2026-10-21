/**
 * Экран одного задания (панель вьюхи «Оценки»): тап по строке ДЗ в
 * детализации предмета открывает КОНКРЕТНОЕ задание здесь — без прыжка
 * на вкладку «Задания» (для этого есть навигация снизу, решение Миши
 * 2026-10-21).
 *
 * Тело задания рендерит HomeworkRowItem (та же карточка, что в списке
 * «Заданий», сразу раскрытая: autoExpand). Сдача/чат/материалы работают
 * без изменений; onUpdated обновляет задание после сдачи.
 */
import React from 'react';
import {
  Panel, PanelHeader, IconButton, Spinner, Placeholder, Button,
} from '@vkontakte/vkui';
import { Icon28ChevronBack, Icon56DocumentOutline } from '@vkontakte/icons';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { HomeworkRowItem } from '@/shared/components/HomeworkCardList';
import { childQuery } from '@/shared/lib/store';
import type { HomeworkItem } from '@/shared/lib/types';

interface AssignmentPageProps {
  id: string;
  assignmentId: number | null;
  onBack: () => void;
  /** Сдавать может только ученик (как на вкладке «Заданий»). */
  canSubmit?: boolean;
}

export const AssignmentPage: React.FC<AssignmentPageProps> = ({
  id, assignmentId, onBack, canSubmit = true,
}) => {
  const addToast = useToast();
  const [item, setItem] = React.useState<HomeworkItem | null>(null);
  const [loading, setLoading] = React.useState(true);

  const load = React.useCallback(async () => {
    if (assignmentId == null) return;
    setLoading(true);
    try {
      const res = await apiGet<{ homework?: HomeworkItem; error?: string }>(
        `/rost_max/api/homework/${assignmentId}?_t=1${childQuery()}`);
      if (res.error) {
        setItem(null);
        addToast(res.error, 'error');
      } else {
        setItem(res.homework ?? null);
      }
    } catch {
      setItem(null);
      addToast('Не удалось загрузить задание', 'error');
    } finally {
      setLoading(false);
    }
  }, [assignmentId, addToast]);

  React.useEffect(() => { load(); }, [load]);

  return (
    <Panel id={id}>
      <PanelHeader
        before={<IconButton label="Назад" onClick={onBack}><Icon28ChevronBack /></IconButton>}
      >
        Задание
      </PanelHeader>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spinner size="l" />
        </div>
      ) : !item ? (
        <Placeholder icon={<Icon56DocumentOutline />} title="Задание не найдено">
          <Button mode="outline" stretched onClick={load}>Повторить</Button>
        </Placeholder>
      ) : (
        <div style={{ margin: '8px 8px 8px' }}>
          <HomeworkRowItem
            h={item}
            canSubmit={canSubmit && item.state !== 'accept' && item.state !== 'submit'}
            onSubmit={async (hid, answer, files) => {
              try {
                const res = await apiPost<{ success?: boolean; error?: string }>(
                  `/rost_max/api/homework/${hid}/submit`, { answer, files });
                if (res.error) {
                  addToast(res.error, 'error');
                  return res.error;
                }
                addToast('Домашнее задание сдано', 'success');
                load();
                return null;
              } catch {
                addToast('Не удалось сдать задание', 'error');
                return 'error';
              }
            }}
            onUpdated={load}
            autoExpand
          />
        </div>
      )}
    </Panel>
  );
};
