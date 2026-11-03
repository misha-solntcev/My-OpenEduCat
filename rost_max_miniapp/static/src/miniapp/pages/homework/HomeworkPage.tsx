/**
 * Вкладка «Задания» (ученик/родитель): сегмент-контрол статусов —
 * «Новые» (не сдано, включая «на доработку» с комментарием учителя) /
 * «На проверке» (сдано, ждёт проверки) / «Проверено» (принято). Ниже — список только
 * выбранного статуса (тот же паттерн, что у учителя и в ReviewQueue).
 */
import React from 'react';
import { Panel, Div, Spinner, Button, Placeholder, Caption } from '@vkontakte/vkui';
import { Icon56DocumentOutline } from '@vkontakte/icons';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { useAppStore, childQuery } from '@/shared/lib/store';
import { HomeworkCardList } from '@/shared/components/HomeworkCardList';
import { AccentSegmentedControl } from '@/shared/components/AccentSegmentedControl';
import type { HomeworkItem, HomeworkListResponse } from '@/shared/lib/types';

import { TabHeader } from '@/shared/components/TabHeader';
import { useViewerAxis, viewerChips, viewerFromDraft } from '@/shared/lib/viewerAxis';
import { ChipFilterModal, FilterChipRow, FilterIconButton } from '@/shared/components/ChipFilterModal';
import type { ChipFilterSection } from '@/shared/components/ChipFilterModal';

interface HomeworkPageProps {
  id: string;
  /** Сдавать может только ученик (правило бэка): родитель и учитель
   *  в режиме ребёнка получают false — кнопка «Сдать» не рисуется. */
  canSubmit?: boolean;
  onOpenProfile?: () => void;
  /** id задания для глубокого входа (тап по строке ДЗ в «Оценках»):
   *  карточка раскрывается сразу, сегмент переключается на статус этого
   *  задания (принято -> «Проверено», сдано -> «На проверке»). */
  autoExpandId?: number | null;
}

type StatusKey = 'fresh' | 'submitted' | 'checked';

/** Сегмент-контрол статусов: подпись, цветная точка, текст пустого списка. */
const SEGMENTS: { key: StatusKey; title: string; empty: string }[] = [
  { key: 'fresh', title: 'Новые', empty: 'Новых заданий нет' },
  { key: 'submitted', title: 'На проверке', empty: 'Нет заданий, ожидающих проверки' },
  { key: 'checked', title: 'Проверено', empty: 'Проверенных заданий пока нет' },
];

/** Группировка по состоянию сдачи.
 *
 * Новые: ещё не сдано (none/draft), включая «на доработку» (change/reject)
 * с комментарием учителя — их нужно переделать и пересдать.
 * На проверке: submit, ждёт проверки. Проверено: принято.
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

export const HomeworkPage: React.FC<HomeworkPageProps> = ({ id, canSubmit = true, onOpenProfile, autoExpandId }) => {
  const addToast = useToast();
  // Ось «Кого смотрим» (свитч удалён — решение 2026-10-14): только у
  // родителя 2+ и staff-родителя — у чистого ученика оси нет.
  const axis = useViewerAxis();
  const [filtersOpen, setFiltersOpen] = React.useState(false);
  const selectedChildId = useAppStore(s => s.selectedChildId);
  const [items, setItems] = React.useState<HomeworkItem[] | null>(null);
  const [loading, setLoading] = React.useState(false);
  // Активный сегмент статуса (сегмент-контрол как у учителя/ReviewQueue).
  const [status, setStatus] = React.useState<StatusKey>('fresh');
  // Четверть: по умолчанию текущая (сервер её же и возвращает, если номер
  // не передан; в каникулы — предыдущая). Выбор живёт в шторке фильтров
  // ПЕРВОЙ секцией — единый паттерн с «Оценками» и учительскими экранами.
  const [quarter, setQuarter] = React.useState<number | null>(null);
  const [currentQuarter, setCurrentQuarter] = React.useState<number | null>(null);
  const [quarters, setQuarters] = React.useState<{ q: number; name: string }[]>([]);

  // q: номер четверти; null/undefined — спросить сервер (он отдаст текущую).
  const load = React.useCallback(async (q?: number | null) => {
    const qn = typeof q === 'number' ? q : null;
    setLoading(true);
    try {
      const cq = childQuery();
      const parts: string[] = [];
      if (cq) parts.push(cq.replace(/^[?&]/, ''));
      if (qn) parts.push(`quarter=${qn}`);
      const qs = parts.length ? `?${parts.join('&')}` : '';
      const res = await apiGet<HomeworkListResponse>(
        `/rost_max/api/homework${qs}`);
      setItems(res.homework || []);
      setQuarters(res.quarters || []);
      setQuarter(res.quarter ?? qn ?? null);
      setCurrentQuarter(res.current_quarter ?? null);
    } catch {
      addToast('Не удалось загрузить задания', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, selectedChildId]);

  React.useEffect(() => { load(); }, [load]);

  // Четверть — ПЕРВАЯ секция шторки фильтров (решение 2026-11): значение
  // одно (singe), по умолчанию текущая; в каникулы сервер отдаёт предыдущую.
  const sheetSections: ChipFilterSection[] = React.useMemo(() => ([
    ...(quarters.length > 1 ? [{
      key: 'quarter',
      header: 'Четверть',
      single: true,
      options: quarters.map(qq => ({
        value: String(qq.q), label: `${qq.q} четверть`,
      })),
    }] : []),
    ...(axis ? [axis.section] : []),
  ]), [quarters, axis]);

  const filterActive = Boolean(
    (quarter != null && currentQuarter != null && quarter !== currentQuarter)
    || axis?.nonDefault,
  );

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

  // Глубокий вход из «Оценок»: сегмент переключается на статус задания,
  // иначе autoExpand-карточка не в списке активного сегмента и не видна.
  // Эффект один раз на каждое новое autoExpandId (lastApplied — как у
  // initialFilter в TeacherHomeworkPage, без него повторный тап по той же
  // строке не сработал бы).
  const lastExpandRef = React.useRef<number | null>(null);
  React.useEffect(() => {
    if (autoExpandId == null || lastExpandRef.current === autoExpandId) return;
    lastExpandRef.current = autoExpandId;
    const it = (items || []).find(x => x.id === autoExpandId);
    if (it) {
      if (it.state === 'accept') setStatus('checked');
      else if (it.state === 'submit') setStatus('submitted');
    }
  }, [autoExpandId, items]);

  return (
    <Panel id={id}>
      {/* Корневой таб: без PanelHeader — активный таб виден в таббаре.
          Аватар «кто смотрит» слева (решение 2026-10-14), тап — профиль. */}
      <TabHeader
        title="Задания"
        onOpenProfile={onOpenProfile}
        after={(
          <FilterIconButton
            active={filterActive}
            expanded={filtersOpen}
            onClick={() => setFiltersOpen(true)}
          />
        )}
      />
      {(quarter != null || axis) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 16px 4px' }}>
          <FilterChipRow
            chips={[
              ...(quarter != null
                ? [{ kind: 'quarter', v: `${quarter} четверть`, removable: false }]
                : []),
              ...(axis ? viewerChips(axis) : []),
            ]}
            onRemove={() => axis?.apply('school')}
            onReset={() => {
              if (axis) axis.apply('school');
              load(currentQuarter ?? undefined);
            }}
          />
        </div>
      )}
      {loading && !items ? (
        <Div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spinner size="l" />
        </Div>
      ) : !items ? (
        <Div>
          <Button mode="outline" stretched onClick={() => load()}>Повторить</Button>
        </Div>
      ) : items.length === 0 ? (
        <Placeholder icon={<Icon56DocumentOutline />} title="Заданий нет">
          <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
            Новых домашних заданий не задано.
          </Caption>
        </Placeholder>
      ) : (
        <>
          {/* Сегмент-контрол статусов (общий AccentSegmentedControl). */}
          <div style={{ paddingInline: 12, paddingTop: 10, paddingBottom: 10 }}>
            <AccentSegmentedControl
              aria-label="Статусы заданий"
              value={status}
              onChange={setStatus}
              options={SEGMENTS.map(({ key, title }) => ({
                value: key, title, count: groups[key].length,
              }))}
            />
          </div>

          {groups[status].length > 0 ? (
            <HomeworkCardList
              items={groups[status]}
              canSubmit={canSubmit && status === 'fresh'}
              onSubmit={submit}
              onUpdated={load}
              autoExpandId={autoExpandId}
            />
          ) : (
            <Caption style={{ display: 'block', padding: '16px 16px 24px', color: 'var(--vkui--color_text_secondary)' }}>
              {SEGMENTS.find(s => s.key === status)!.empty}
            </Caption>
          )}
        </>
      )}
      {/* Шторка фильтров: четверть ПЕРВОЙ секцией, дальше ось «Кого
          смотрим» (у чистого ученика её нет). */}
      <ChipFilterModal
        open={filtersOpen}
        id="homework-filters"
        sections={sheetSections}
        value={{
          quarter: new Set(quarter != null ? [String(quarter)] : []),
          viewer: new Set(axis ? [axis.value] : []),
        }}
        footerOrder="cancel-first"
        onClose={() => setFiltersOpen(false)}
        onApply={f => {
          const qv = Number([...(f.quarter ?? new Set<string>())][0]);
          if (axis) axis.apply(viewerFromDraft(f.viewer, axis));
          setFiltersOpen(false);
          if (qv && qv !== quarter) {
            setQuarter(qv);
            load(qv);
          }
        }}
      />
    </Panel>
  );
};
