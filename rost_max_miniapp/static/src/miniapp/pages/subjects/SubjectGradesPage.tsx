import React from 'react';
import {
  Panel,
  PanelHeader,
  IconButton,
  Box,
  Flex,
  Text,
  Spinner,
  Group,
  SimpleCell,
  Placeholder,
  Badge,
  Footnote,
} from '@vkontakte/vkui';
import { Icon28ChevronBack, Icon56NotebookCheckOutline } from '@vkontakte/icons';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import type { MyGradesResponse } from '@/shared/lib/types';

interface SubjectGradesPageProps {
  id: string;
  subjectId: number;
  subjectName: string;
  onBack: () => void;
}

const fmtDate = (iso: string): string => {
  if (!iso) return '';
  return new Date(iso + 'T00:00:00').toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long',
  });
};

/** Детализация предмета: сводка четверти + хронология оценок/посещаемости */
export const SubjectGradesPage: React.FC<SubjectGradesPageProps> = ({
  id,
  subjectId,
  subjectName,
  onBack,
}) => {
  const addToast = useToast();
  const [data, setData] = React.useState<MyGradesResponse | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<MyGradesResponse>(`/rost_max/api/my/grades/${subjectId}`)
      .then(res => { if (!cancelled) setData(res); })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          addToast('Не удалось загрузить оценки', 'error');
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [subjectId, addToast]);

  return (
    <Panel id={id}>
      <PanelHeader
        before={<IconButton label="Назад" onClick={onBack}><Icon28ChevronBack /></IconButton>}
      >
        {subjectName}
      </PanelHeader>

      <Box padding="m">
        {loading ? (
          <Flex padding="xl" align="center" justify="center">
            <Spinner size="l" />
          </Flex>
        ) : !data || data.lines.length === 0 ? (
          <Placeholder icon={<Icon56NotebookCheckOutline />}>
            <Text weight="2">Оценок пока нет</Text>
            <Footnote>За выбранную четверть записей по предмету нет.</Footnote>
          </Placeholder>
        ) : (
          <>
            <Flex gap={8} paddingBlockEnd="m" wrap="wrap">
              <Badge>Средняя: {data.summary.average_mark > 0 ? data.summary.average_mark.toFixed(2) : '—'}</Badge>
              <Badge>Посещаемость: {data.summary.attendance_rate.toFixed(0)}%</Badge>
              <Badge>Уроков: {data.summary.total_classes}</Badge>
            </Flex>

            <Group header="Оценки и посещаемость">
              {data.lines.map(ln => (
                <SimpleCell
                  key={ln.line_id}
                  before={fmtDate(ln.date)}
                  after={
                    <Flex gap={2}>
                      {ln.grades.map((g, i) => (
                        <Text key={i} weight="2">{g}</Text>
                      ))}
                    </Flex>
                  }
                  subtitle={ln.attendance ?? ''}
                >
                  {ln.topic || ln.subject}
                </SimpleCell>
              ))}
            </Group>

            {data.summary.last_remark && data.summary.last_remark !== '—' && (
              <Box padding="m" paddingBlockStart="s">
                <Text color="secondary">Последний комментарий: {data.summary.last_remark}</Text>
              </Box>
            )}
          </>
        )}
      </Box>
    </Panel>
  );
};
