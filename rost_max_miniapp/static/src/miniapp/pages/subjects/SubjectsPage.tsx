import React from 'react';
import {
  Panel,
  PanelHeader,
  Box,
  Flex,
  Text,
  Spinner,
  Group,
  SimpleCell,
  Placeholder,
  SegmentedControl,
  Avatar,
  Footnote,
} from '@vkontakte/vkui';
import { Icon56UserBookOutline } from '@vkontakte/icons';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import type { MySubjectsResponse, SubjectSummary } from '@/shared/lib/types';

interface SubjectsPageProps {
  id: string;
  onOpenSubject: (subjectId: number, subjectName: string) => void;
}

const fmtAvg = (v: number): string => v > 0 ? v.toFixed(2) : '—';

/** Экран «Успеваемость» (ученик / родитель): предметы → детализация */
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

  // Грузим один раз при монтировании (quarter на этом экране не меняется)
  React.useEffect(() => { load(quarter); }, []);

  const subjects: SubjectSummary[] = data?.students[0]?.subjects ?? [];
  const studentName = data?.students[0]?.name ?? '';

  return (
    <Panel id={id}>
      <PanelHeader>Успеваемость</PanelHeader>

      <Box padding="m">
        {loading ? (
          <Flex padding="xl" align="center" justify="center">
            <Spinner size="l" />
          </Flex>
        ) : !data || subjects.length === 0 ? (
          <Placeholder icon={<Icon56UserBookOutline />}>
            <Text weight="2">Нет данных за четверть</Text>
            <Footnote>Оценки появятся, когда учитель заполнит журнал.</Footnote>
          </Placeholder>
        ) : (
          <>
            {/* Переключатель четвертей */}
            {data.quarters.length > 1 && (
              <Box paddingBlockEnd="m">
                <SegmentedControl
                  value={String(quarter)}
                  options={data.quarters.map(qq => ({
                    label: `${qq.q} четверть`,
                    value: String(qq.q),
                  }))}
                  onChange={(v) => load(Number(v))}
                />
              </Box>
            )}

            {studentName && (
              <Flex align="center" gap={8} paddingBlockEnd="m">
                <Avatar size={32} initials={studentName.split(' ').map(p => p[0]).slice(0, 2).join('')} />
                <Text weight="2">{studentName}</Text>
              </Flex>
            )}

            <Group header="Предметы">
              {subjects.map(s => (
                <SimpleCell
                  key={s.subject_id}
                  onClick={() => onOpenSubject(s.subject_id, s.name)}
                  after={<Text weight="2">{fmtAvg(s.average_mark)}</Text>}
                  subtitle={`Посещаемость: ${s.attendance_rate.toFixed(0)}% (${s.present_classes}/${s.total_classes})`}
                >
                  {s.name}
                </SimpleCell>
              ))}
            </Group>
          </>
        )}
      </Box>
    </Panel>
  );
};
