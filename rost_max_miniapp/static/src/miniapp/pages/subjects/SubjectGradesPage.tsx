import React from 'react';
import {
  Panel,
  PanelHeader,
  IconButton,
  Box,
  Flex,
  Text,
  Spinner,
  Placeholder,
  Footnote,
  Card as VkCard,
} from '@vkontakte/vkui';
import { Icon28ChevronBack, Icon56NotebookCheckOutline } from '@vkontakte/icons';
import { apiGet } from '@/shared/lib/api';
import { JournalButton } from '@/shared/components/JournalButton';
import { SubjectAvatar } from '@/shared/components/SubjectIcon';
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
  const [, month, day] = iso.split('-');
  return `${day}.${month}`;
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
        {data ? (
          <Flex align="center" gap={10}>
            <SubjectAvatar subject={subjectName} color={data.subject_color} size={30} />
            <Text weight="2" style={{ fontSize: 18 }}>{subjectName}</Text>
          </Flex>
        ) : (
          <Text weight="2" style={{ fontSize: 18 }}>{subjectName}</Text>
        )}
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
            <Flex gap={8} align="stretch" style={{ marginBottom: 12 }}>
              {[
                { label: 'Уроков', value: String(data.summary.total_classes) },
                { label: 'Посещаемость', value: `${data.summary.attendance_rate.toFixed(0)}%` },
                { label: 'Средний балл', value: data.summary.average_mark > 0 ? data.summary.average_mark.toFixed(2).replace('.', ',') : '—' },
              ].map((item) => (
                <VkCard
                  key={item.label}
                  mode="shadow"
                  style={{ flex: 1, minWidth: 0, padding: 12, textAlign: 'center' }}
                >
                  <Text color="secondary" style={{ display: 'block', fontSize: 12, lineHeight: 1.2 }}>
                    {item.label}
                  </Text>
                  <Text weight="2" style={{ display: 'block', fontSize: 22, lineHeight: 1.2, marginTop: 6 }}>
                    {item.value}
                  </Text>
                </VkCard>
              ))}
            </Flex>

            <div>
              {data.lines.map((ln) => (
                <VkCard
                  key={ln.line_id}
                  mode="shadow"
                  style={{ padding: 12, marginBottom: 8, borderRadius: 12 }}
                >
                  <Flex align="center" gap={10} alignItems="flex-start">
                    <Text weight="1" style={{ color: 'var(--vkui--color_text_secondary)', whiteSpace: 'nowrap', minWidth: 42 }}>
                      {fmtDate(ln.date)}
                    </Text>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Text style={{ display: 'block', lineHeight: 1.35 }}>{ln.topic || 'Тема не указана'}</Text>
                      {(ln.attendance_type_id || ln.grades.length > 0) && (
                        <Flex gap={4} align="center" wrap="wrap" style={{ marginTop: 8 }}>
                          {ln.attendance_type_id && (
                            <JournalButton
                              kind="attendance"
                              value={ln.attendance_type_id}
                              attendanceTypes={[{ id: ln.attendance_type_id, name: ln.attendance || '' }]}
                              size="m"
                            />
                          )}
                          {ln.grades.map((g, i) => (
                            <JournalButton key={`${g}-${i}`} kind="grade" value={g} size="m" />
                          ))}
                        </Flex>
                      )}
                    </div>
                  </Flex>
                </VkCard>
              ))}
            </div>

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
