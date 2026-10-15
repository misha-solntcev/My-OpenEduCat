import React from 'react';
import {
  Panel,
  Box,
  Flex,
  Text,
  Spinner,
  Placeholder,
  SegmentedControl,
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
import { useViewerAxis, viewerFromDraft } from '@/shared/lib/viewerAxis';
import { ChipFilterModal, FilterChipRow, FilterIconButton } from '@/shared/components/ChipFilterModal';

interface SubjectsPageProps {
  id: string;
  onOpenSubject: (subjectId: number, subjectName: string) => void;
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
  const [viewerOpen, setViewerOpen] = React.useState(false);
  const selectedChildId = useAppStore(s => s.selectedChildId);
  const [data, setData] = React.useState<MySubjectsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [quarter, setQuarter] = React.useState<number | null>(null);

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
    } catch {
      setData(null);
      addToast('Не удалось загрузить успеваемость', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, selectedChildId]);

  React.useEffect(() => { load(quarter); }, [load]);

  const subjects: SubjectSummary[] = data?.students[0]?.subjects ?? [];

  return (
    <Panel id={id}>
      <Box padding="m">
        {/* Аватар «кто смотрит» слева (решение 2026-10-14), тап — профиль;
            кнопка фильтра справа — у кого есть ось «Кого смотрим». */}
        <TabHeader
          title="Оценки"
          onOpenProfile={onOpenProfile}
          after={axis ? (
            <FilterIconButton
              active={axis.nonDefault}
              expanded={viewerOpen}
              onClick={() => setViewerOpen(true)}
            />
          ) : undefined}
        />
        {axis && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 0 4px' }}>
            <FilterChipRow
              chips={[{ kind: 'viewer', v: axis.chipLabel, removable: axis.chipRemovable }]}
              onRemove={() => axis.apply('mine')}
            />
          </div>
        )}
        {loading ? (
          <Flex padding="xl" align="center" justify="center"><Spinner size="l" /></Flex>
        ) : !data || subjects.length === 0 ? (
          <>
            {data && data.quarters.length > 1 && (
              <Box paddingBlockEnd="m">
                <SegmentedControl
                  value={String(quarter)}
                  options={data.quarters.map(qq => ({ label: `${qq.q} четверть`, value: String(qq.q) }))}
                  onChange={(v) => load(Number(v))}
                />
              </Box>
            )}
            <Placeholder icon={<Icon56UserBookOutline />}>
              <Text weight="2">Нет данных за четверть</Text>
              <Caption>Оценки появятся, когда учитель заполнит журнал.</Caption>
            </Placeholder>
          </>
        ) : (
          <>
            {data.quarters.length > 1 && (
              <Box paddingBlockEnd="m">
                <SegmentedControl value={String(quarter)} options={data.quarters.map(qq => ({ label: `${qq.q} четверть`, value: String(qq.q) }))} onChange={(v) => load(Number(v))} />
              </Box>
            )}
            <VkCard mode="shadow" style={{ padding: 14, marginBottom: 12 }}>
              <Flex align="center" justify="space-between">
                <div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Средний балл за четверть</Caption><Text weight="2" style={{ display: 'block', fontSize: 34, lineHeight: 1.15, marginTop: 3 }}>{fmtAvg(data.overall_average)}</Text></div>
              </Flex>
            </VkCard>
            <Div>
              {subjects.map(subject => <SubjectGradeCard key={subject.subject_id} subject={subject} onClick={() => onOpenSubject(subject.subject_id, subject.name)} />)}
            </Div>
          </>
        )}
      </Box>
      {/* Шторка «Кого смотрим» — ось режима (решение 2026-10-14).
          GUARD обязателен: у ученика axis=null. */}
      {axis && (
      <ChipFilterModal
        open={viewerOpen}
        id="subjects-viewer"
        sections={[axis.section]}
        value={{ viewer: new Set([axis.value]) }}
        footerOrder="cancel-first"
        onClose={() => setViewerOpen(false)}
        onApply={f => {
          axis.apply(viewerFromDraft(f.viewer, axis));
          setViewerOpen(false);
        }}
      />
      )}
    </Panel>
  );
};
