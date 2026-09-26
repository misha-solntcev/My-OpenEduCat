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
import { SubjectAvatar } from '@/shared/components/SubjectIcon';
import { getGradeAppearance } from '@/shared/lib/cycle';
import type { MySubjectsResponse, SubjectSummary } from '@/shared/lib/types';

interface SubjectsPageProps {
  id: string;
  onOpenSubject: (subjectId: number, subjectName: string) => void;
}

const fmtAvg = (v: number): string => v > 0 ? v.toFixed(2).replace('.', ',') : '—';
const fmtGradeDate = (date: string): string => {
  if (!date) return '';
  const [, month, day] = date.split('-');
  return `${day}.${month}`;
};

const gradeTone = (grade: number): React.CSSProperties => {
  const appearance = getGradeAppearance(grade);
  if (appearance === 'positive') return { background: 'var(--vkui--color_background_positive_tint)', borderColor: 'var(--vkui--color_stroke_positive)', color: 'var(--vkui--color_text_positive)' };
  if (appearance === 'accent') return { background: 'var(--vkui--color_background_accent_tint)', borderColor: 'var(--vkui--color_stroke_accent)', color: 'var(--vkui--color_text_primary)' };
  if (appearance === 'warning') return { background: 'var(--vkui--color_background_warning)', borderColor: 'var(--vkui--color_icon_warning)', color: 'var(--vkui--color_text_primary)' };
  return { background: 'var(--vkui--color_background_negative_tint)', borderColor: 'var(--vkui--color_stroke_negative)', color: 'var(--vkui--color_text_negative)' };
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
              <span style={{ ...gradeTone(item.grade), minWidth: 30, height: 30, padding: '0 8px', borderRadius: 9, border: '1px solid', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700 }}>{item.grade}</span>
              <Caption style={{ color: 'var(--vkui--color_text_secondary)', fontSize: 10, lineHeight: 1 }}>{fmtGradeDate(item.date)}</Caption>
            </span>
          ))}
        </Flex>
      </div>
    </Flex>
  </VkCard>
);

/** Экран «Успеваемость» (ученик / родитель): сводка → карточки предметов. */
export const SubjectsPage: React.FC<SubjectsPageProps> = ({ id, onOpenSubject }) => {
  const addToast = useToast();
  const [data, setData] = React.useState<MySubjectsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [quarter, setQuarter] = React.useState<number | null>(null);

  const load = React.useCallback(async (q: number | null) => {
    setLoading(true);
    try {
      const url = q ? `/rost_max/api/my/subjects?quarter=${q}` : '/rost_max/api/my/subjects';
      const res = await apiGet<MySubjectsResponse>(url);
      setData(res);
      setQuarter(res.quarter);
    } catch {
      setData(null);
      addToast('Не удалось загрузить успеваемость', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  React.useEffect(() => { load(quarter); }, [load]);

  const subjects: SubjectSummary[] = data?.students[0]?.subjects ?? [];

  return (
    <Panel id={id}>
      <Box padding="m">
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
    </Panel>
  );
};
