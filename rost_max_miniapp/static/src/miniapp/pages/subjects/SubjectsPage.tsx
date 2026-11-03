import React from 'react';
import {
  Panel,
  Box,
  Flex,
  Text,
  Spinner,
  Placeholder,
  Card as VkCard,
  Div,
  Caption,
} from '@vkontakte/vkui';
import { Icon56UserBookOutline } from '@vkontakte/icons';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { useAppStore, childQuery } from '@/shared/lib/store';
import { SubjectAvatar } from '@/shared/components/SubjectIcon';
import { GradeChip } from '@/shared/components/JournalButton';
import type { MySubjectsResponse, SubjectSummary } from '@/shared/lib/types';
import { TabHeader } from '@/shared/components/TabHeader';
import { useViewerAxis, viewerChips, viewerFromDraft } from '@/shared/lib/viewerAxis';
import { ChipFilterModal, FilterChipRow, FilterIconButton } from '@/shared/components/ChipFilterModal';
import type { ChipFilterSection } from '@/shared/components/ChipFilterModal';

interface SubjectsPageProps {
  id: string;
  onOpenSubject: (subjectId: number, subjectName: string, quarter?: number) => void;
  onOpenProfile?: () => void;
}

const fmtAvg = (v: number): string => v > 0 ? v.toFixed(2).replace('.', ',') : '—';
const fmtGradeDate = (date: string): string => {
  if (!date) return '';
  const [, month, day] = date.split('-');
  return `${day}.${month}`;
};

const SubjectGradeCard: React.FC<{ subject: SubjectSummary; onClick: () => void }> = ({ subject, onClick }) => (
  <VkCard mode="shadow" onClick={onClick} style={{ margin: '0 0 8px', padding: 12, cursor: 'pointer' }}>
    <Flex align="start" gap={10}>
      <SubjectAvatar subject={subject.name} color={subject.subject_color} size={40} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <Flex align="center" justify="space-between" gap={8}>
          <Text weight="2" style={{ fontSize: 16, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{subject.name}</Text>
          <Text weight="2" style={{ fontSize: 17, whiteSpace: 'nowrap' }}>{fmtAvg(subject.average_mark)}</Text>
        </Flex>
        <Flex gap={5} align="start" style={{ marginTop: 10, overflow: 'hidden', whiteSpace: 'nowrap' }}>
          {subject.latest_grades.length === 0 ? (
            <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Оценок пока нет</Caption>
          ) : subject.latest_grades.map((item, index) => (
            <span key={`${item.date}-${item.grade}-${index}`} style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 3, flexShrink: 0 }}>
              <GradeChip grade={item.grade} size="m" />
              <Caption style={{ color: 'var(--vkui--color_text_secondary)', fontSize: 10, lineHeight: 1 }}>{fmtGradeDate(item.date)}</Caption>
            </span>
          ))}
        </Flex>
      </div>
    </Flex>
  </VkCard>
);

/** Экран «Успеваемость» (ученик / родитель): сводка → карточки предметов. */
export const SubjectsPage: React.FC<SubjectsPageProps> = ({ id, onOpenSubject, onOpenProfile }) => {
  const addToast = useToast();
  // Ось «Кого смотрим» (свитч удалён — решение 2026-10-14).
  const axis = useViewerAxis();
  const [filtersOpen, setFiltersOpen] = React.useState(false);
  const selectedChildId = useAppStore(s => s.selectedChildId);
  const [data, setData] = React.useState<MySubjectsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [quarter, setQuarter] = React.useState<number | null>(null);
  const [currentQuarter, setCurrentQuarter] = React.useState<number | null>(null);

  const load = React.useCallback(async (q: number | null) => {
    setLoading(true);
    try {
      // Параметры собираю явно: childQuery() отдаёт '&child_id=N',
      // на энпоинте без '?' наивная конкатенация даёт 404.
      const params: string[] = [];
      if (q) params.push(`quarter=${q}`);
      const cq = childQuery();
      if (cq) params.push(cq.slice(1));
      const res = await apiGet<MySubjectsResponse>(
        `/rost_max/api/my/subjects${params.length ? '?' + params.join('&') : ''}`);
      setData(res);
      setQuarter(res.quarter);
      setCurrentQuarter(res.current_quarter ?? null);
    } catch {
      setData(null);
      addToast('Не удалось загрузить успеваемость', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, selectedChildId]);

  React.useEffect(() => { load(quarter); }, [load]);

  const subjects: SubjectSummary[] = data?.students[0]?.subjects ?? [];

  // Четверть — ПЕРВАЯ секция шторки фильтров (решение 2026-11): одно
  // значение, по умолчанию текущая; в каникулы сервер отдаёт предыдущую.
  const sheetSections: ChipFilterSection[] = React.useMemo(() => ([
    ...((data?.quarters?.length ?? 0) > 1 ? [{
      key: 'quarter',
      header: 'Четверть',
      single: true,
      options: (data?.quarters ?? []).map(qq => ({
        value: String(qq.q), label: `${qq.q} четверть`,
      })),
    }] : []),
    ...(axis ? [axis.section] : []),
  ]), [data?.quarters, axis]);

  const filterActive = Boolean(
    (quarter != null && currentQuarter != null && quarter !== currentQuarter)
    || axis?.nonDefault,
  );

  return (
    <Panel id={id}>
      <Box padding="m">
        {/* Аватар «кто смотрит» слева (решение 2026-10-14), тап — профиль;
            кнопка фильтра справа — у кого есть ось «Кого смотрим». */}
        <TabHeader
          title="Оценки"
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 0 4px' }}>
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
                load(currentQuarter);
              }}
            />
          </div>
        )}
        {loading ? (
          <Flex padding="xl" align="center" justify="center"><Spinner size="l" /></Flex>
        ) : !data || subjects.length === 0 ? (
          <>
            <Placeholder icon={<Icon56UserBookOutline />}>
              <Text weight="2">Нет данных за четверть</Text>
              <Caption>Оценки появятся, когда учитель заполнит журнал.</Caption>
            </Placeholder>
          </>
        ) : (
          <>
            <VkCard mode="shadow" style={{ padding: 14, marginBottom: 12 }}>
              <Flex align="center" justify="space-between">
                <div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Средний балл за четверть</Caption><Text weight="2" style={{ display: 'block', fontSize: 34, lineHeight: 1.15, marginTop: 3 }}>{fmtAvg(data.overall_average)}</Text></div>
              </Flex>
            </VkCard>
            <Div>
              {subjects.map(subject => <SubjectGradeCard key={subject.subject_id} subject={subject} onClick={() => onOpenSubject(subject.subject_id, subject.name, quarter ?? undefined)} />)}
            </Div>
          </>
        )}
      </Box>
      {/* Шторка фильтров: четверть ПЕРВОЙ секцией; ось «Кого смотрим» —
          у родителя 2+ и staff-родителя. GUARD: у ученика axis=null. */}
      <ChipFilterModal
        open={filtersOpen}
        id="subjects-filters"
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
          if (qv && qv !== quarter) load(qv);
        }}
      />
    </Panel>
  );
};
