/**
 * Вкладка «Задания» учителя/админа (по образцу Google Classroom).
 *
 * Сегменты: «К проверке» (есть сдачи submit) / «Активные» (publish) /
 * «Завершённые» (finish). Никаких временных окон — полный список,
 * свежие сверху. Клик по заданию — экран задания: карточка, правка
 * (текст/срок/флаг), «Завершить приём», SubmissionReviewCard.
 *
 * Правка текста идёт через журнал-источник (sheet.lesson_homework) —
 * синк rost_lesson_homework обновит задание и перезапишет пост в
 * канале класса; на бэке это POST /homework/<id>/edit.
 */
import React from 'react';
import {
  Panel, PanelHeader, PanelHeaderBack, Div, Spinner, Button, Placeholder,
  Caption, Text, Card as VkCard, Counter, Input, Checkbox, SegmentedControl,
  Textarea, Header, SimpleCell,
} from '@vkontakte/vkui';
import {
  Icon56DocumentOutline, Icon28EditOutline, Icon28AttachOutline,
} from '@vkontakte/icons';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useAppStore } from '@/shared/lib/store';
import { useToast } from '@/shared/components/Toast';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { SubmissionReviewCard } from '@/pages/dashboard/components/feed';
import type {
  TeacherHomeworkItem, TeacherHomeworkResponse, HomeworkSubmissionsResponse,
} from '@/shared/lib/types';

const MONTHS = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн',
  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

const fmtDue = (due: string): string => {
  if (!due) return '';
  const d = new Date(due);
  if (isNaN(d.getTime())) return due;
  return `до ${d.getDate()} ${MONTHS[d.getMonth()]}`;
};

type Segment = 'review' | 'active' | 'finished';

/** Чип-счётчики строки задания. */
const RowChips: React.FC<{ h: TeacherHomeworkItem }> = ({ h }) => (
  <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
    {h.to_review > 0 && h.state === 'publish' && (
      <Counter mode="primary" appearance="accent-red">{`${h.to_review} к проверке`}</Counter>
    )}
    <Counter mode="primary" appearance={h.state === 'finish' ? 'neutral' : undefined}>
      {`Сдали ${h.submitted} из ${h.total}`}
    </Counter>
  </div>
);

/** Строка списка заданий. */
const TeacherHwRow: React.FC<{
  h: TeacherHomeworkItem;
  onOpen: (id: number) => void;
  showFaculty: boolean;
}> = ({ h, onOpen, showFaculty }) => (
  <SimpleCell
    onClick={() => onOpen(h.id)}
    before={
      <span style={{
        width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 2,
        background: h.state === 'finish'
          ? 'var(--vkui--color_background_neutral)'
          : h.submitted >= h.total && h.total > 0
            ? 'var(--vkui--color_background_positive)'
            : 'var(--vkui--color_background_negative)',
      }} />
    }
    after={<RowChips h={h} />}
    subtitle={[
      showFaculty ? h.faculty : `${h.batch} · ${fmtDue(h.due)}`,
      h.answer_required ? 'требуется ответ' : '',
      h.overdue ? 'просрочено' : '',
      h.task.length > 70 ? h.task.slice(0, 70) + '…' : h.task,
    ].filter(Boolean).join(' · ') || undefined}
  >
    <span style={{ color: h.state === 'finish'
      ? 'var(--vkui--color_text_secondary)' : undefined }}>
      {h.subject}{h.state === 'finish' ? ' · завершено' : ''}
    </span>
  </SimpleCell>
);

/** Экран правки задания (шторка-карточка в потоке страницы). */
const EditHomeworkCard: React.FC<{
  h: TeacherHomeworkItem;
  onClose: () => void;
  onSaved: () => void;
}> = ({ h, onClose, onSaved }) => {
  const addToast = useToast();
  const [task, setTask] = React.useState(h.task);
  const [dueDate, setDueDate] = React.useState((h.due || '').slice(0, 10));
  const [answerRequired, setAnswerRequired] = React.useState(h.answer_required);
  const [busy, setBusy] = React.useState(false);

  const save = async () => {
    if (!task.trim()) {
      addToast('Текст задания не может быть пустым', 'error');
      return;
    }
    setBusy(true);
    try {
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/homework/${h.id}/edit`,
        {
          task: task.trim(),
          due: dueDate ? `${dueDate} 23:59:00` : '',
          answer_required: answerRequired,
        });
      if (res.error) {
        addToast(res.error, 'error');
        return;
      }
      addToast('Изменения сохранены', 'success');
      onSaved();
      onClose();
    } catch {
      addToast('Не удалось сохранить', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <VkCard mode="shadow" style={{ margin: '0 8px 8px', overflow: 'hidden' }}>
      <div style={{ padding: '12px 16px' }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: 8,
        }}>
          <Text weight="2">Редактирование</Text>
          <span
            style={{
              color: 'var(--vkui--color_text_accent)', cursor: 'pointer',
              fontSize: 13,
            }}
            onClick={onClose}
          >
            Отмена
          </span>
        </div>

        {h.sheet_id == null && (
          <Caption style={{
            color: 'var(--vkui--color_text_secondary)', display: 'block',
            marginBottom: 8,
          }}>
            Задание создано вне журнала — текст правится только в ПК-форме.
          </Caption>
        )}

        <Textarea
          value={task}
          onChange={e => setTask(e.target.value)}
          placeholder="Текст домашнего задания"
          aria-label="Текст задания"
          style={{ marginBottom: 8 }}
        />

        <Caption style={{
          color: 'var(--vkui--color_text_secondary)', display: 'block',
          marginBottom: 4,
        }}>
          Срок сдачи
        </Caption>
        <Input
          type="date"
          value={dueDate}
          onChange={e => setDueDate(e.target.value)}
          aria-label="Срок сдачи"
          style={{ marginBottom: 8 }}
        />

        <Checkbox
          checked={answerRequired}
          onChange={e => setAnswerRequired(e.target.checked)}
        >
          Требуется текстовый ответ
        </Checkbox>

        <Button
          size="l" stretched appearance="accent"
          loading={busy} onClick={save} style={{ marginTop: 8 }}
        >
          Сохранить
        </Button>
      </div>
    </VkCard>
  );
};

/** Экран одного задания: карточка + правка + сдачи. */
const AssignmentDetail: React.FC<{
  assignmentId: number;
  onBack: () => void;
  onListChanged: () => void;
  showFaculty: boolean;
}> = ({ assignmentId, onBack, onListChanged, showFaculty }) => {
  const addToast = useToast();
  const [data, setData] = React.useState<HomeworkSubmissionsResponse | null>(null);
  const [meta, setMeta] = React.useState<TeacherHomeworkItem | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [editing, setEditing] = React.useState(false);
  const [busyFinish, setBusyFinish] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const [list, sub] = await Promise.all([
        apiGet<TeacherHomeworkResponse>('/rost_max/api/teacher_homework'),
        apiGet<HomeworkSubmissionsResponse>(
          `/rost_max/api/homework/${assignmentId}/submissions`),
      ]);
      setMeta(list.homework.find(x => x.id === assignmentId) || null);
      setData(sub);
    } catch {
      addToast('Не удалось загрузить задание', 'error');
    } finally {
      setLoading(false);
    }
  }, [assignmentId, addToast]);

  React.useEffect(() => { load(); }, [load]);

  const toggleFinish = async () => {
    if (!meta) return;
    setBusyFinish(true);
    try {
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/homework/${meta.id}/finish`,
        { action: meta.state === 'publish' ? 'finish' : 'resume' });
      if (res.error) {
        addToast(res.error, 'error');
      } else {
        addToast(meta.state === 'publish'
          ? 'Приём сдач завершён' : 'Приём возобновлён', 'success');
        onListChanged();
        await load();
      }
    } catch {
      addToast('Не удалось изменить состояние', 'error');
    } finally {
      setBusyFinish(false);
    }
  };

  if (loading && !data) {
    return (
      <Panel id="assignment-detail">
        <PanelHeader before={<PanelHeaderBack onClick={onBack} />} />
        <Div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spinner size="l" />
        </Div>
      </Panel>
    );
  }

  return (
    <Panel id="assignment-detail">
      <PanelHeader before={<PanelHeaderBack onClick={onBack} />}>
        {meta ? `${meta.subject} · ${meta.batch}` : 'Задание'}
      </PanelHeader>

      {meta && (
        <VkCard mode="shadow" style={{ margin: '8px 8px 0', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px' }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', marginBottom: 4,
            }}>
              <Text weight="2">
                {showFaculty ? meta.faculty : meta.batch}
              </Text>
              <RowChips h={meta} />
            </div>
            <Caption style={{
              color: 'var(--vkui--color_text_secondary)', display: 'block',
              whiteSpace: 'pre-wrap',
            }}>
              {meta.task}
            </Caption>
            <Caption style={{
              color: 'var(--vkui--color_text_secondary)', display: 'block',
              marginTop: 4,
            }}>
              {[
                fmtDue(meta.due),
                meta.answer_required ? 'требуется ответ' : '',
                meta.state === 'finish' ? 'приём завершён' : '',
              ].filter(Boolean).join(' · ')}
            </Caption>

            {meta.materials_count > 0 && (
              <Caption style={{
                color: 'var(--vkui--color_text_secondary)', display: 'flex',
                alignItems: 'center', gap: 4, marginTop: 4,
              }}>
                <Icon28AttachOutline width={16} height={16} />
                Материалов: {meta.materials_count}
              </Caption>
            )}

            {/* Материалы: просмотр/добавление/удаление (общий редактор). */}
            <MaterialsEditor assignmentId={meta.id} />

            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Button
                size="s" mode="outline"
                before={<Icon28EditOutline />}
                disabled={editing}
                onClick={() => setEditing(true)}
              >
                Редактировать
              </Button>
              {meta.state === 'publish' ? (
                <Button
                  size="s" mode="outline" appearance="negative"
                  loading={busyFinish} onClick={toggleFinish}
                >
                  Завершить приём
                </Button>
              ) : (
                <Button
                  size="s" mode="outline"
                  loading={busyFinish} onClick={toggleFinish}
                >
                  Возобновить
                </Button>
              )}
            </div>
          </div>
        </VkCard>
      )}

      {editing && meta && (
        <EditHomeworkCard
          h={meta}
          onClose={() => setEditing(false)}
          onSaved={onListChanged}
        />
      )}

      {data && (
        <>
          <Header size="s" style={{ marginTop: 8, marginInline: 8 }}>Сдачи класса</Header>
          <SubmissionReviewCard
            submission={data}
            onClose={() => {}}
            onReview={async (subId, action, note, mark) => {
              try {
                const res = await apiPost<{ success?: boolean; error?: string }>(
                  `/rost_max/api/homework/submission/${subId}/review`,
                  { action, teacher_note: note, mark });
                if (res.error) {
                  addToast(res.error, 'error');
                  return res.error;
                }
                addToast(action === 'accept' ? 'Принято' : 'Отправлено на доработку', 'success');
                await load();
                onListChanged();
                return null;
              } catch {
                addToast('Не удалось сохранить проверку', 'error');
                return 'error';
              }
            }}
            onUpdated={() => { load(); onListChanged(); }}
          />
        </>
      )}
    </Panel>
  );
};

export const TeacherHomeworkPage: React.FC<{ id: string }> = ({ id }) => {
  const addToast = useToast();
  const [items, setItems] = React.useState<TeacherHomeworkItem[] | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [segment, setSegment] = React.useState<Segment>('review');
  const [openId, setOpenId] = React.useState<number | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiGet<TeacherHomeworkResponse>(
        '/rost_max/api/teacher_homework');
      setItems(res.homework || []);
    } catch {
      addToast('Не удалось загрузить задания', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  React.useEffect(() => { load(); }, [load]);

  const groups = React.useMemo(() => {
    const all = items || [];
    return {
      review: all.filter(h => h.state === 'publish' && h.to_review > 0),
      active: all.filter(h => h.state === 'publish'),
      finished: all.filter(h => h.state === 'finish'),
    };
  }, [items]);

  const current = groups[segment];

  // Админский список (все ДЗ школы) показывает преподавателя в строке;
  // у учителя свои задания — информативнее класс. Роль — из стора.
  const isAdmin = Boolean(useAppStore(s => s.userInfo)?.is_admin);
  const showFaculty = isAdmin;

  const listChanged = React.useCallback(() => { load(); }, [load]);

  return (
    <Panel id={id}>
      {openId != null ? (
        <AssignmentDetail
          key={openId}
          assignmentId={openId}
          onBack={() => setOpenId(null)}
          onListChanged={listChanged}
          showFaculty={showFaculty}
        />
      ) : (
        <>
          {loading && !items ? (
            <Div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
              <Spinner size="l" />
            </Div>
          ) : !items ? (
            <Div>
              <Button mode="outline" stretched onClick={load}>Повторить</Button>
            </Div>
          ) : (
            <>
              <Div style={{ paddingBottom: 8 }}>
                <SegmentedControl
                  value={segment}
                  onChange={(v: Segment) => setSegment(v)}
                  options={[
                    { label: `К проверке${groups.review.length ? ` · ${groups.review.length}` : ''}`, value: 'review' },
                    { label: `Активные · ${groups.active.length}`, value: 'active' },
                    { label: `Завершённые · ${groups.finished.length}`, value: 'finished' },
                  ]}
                />
              </Div>

              {current.length === 0 ? (
                <Placeholder
                  icon={<Icon56DocumentOutline />}
                  title={segment === 'review' ? 'Всё проверено'
                    : segment === 'active' ? 'Активных заданий нет'
                      : 'Завершённых заданий нет'}
                >
                  <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
                    {segment === 'review'
                      ? 'Новых сдач, ждущих проверки, нет.'
                      : 'Задайте ДЗ из журнала урока.'}
                  </Caption>
                </Placeholder>
              ) : (
                <VkCard mode="shadow" style={{ margin: '0 8px 8px', overflow: 'hidden' }}>
                  {current.map(h => (
                    <TeacherHwRow
                      key={h.id} h={h} onOpen={setOpenId}
                      showFaculty={showFaculty}
                    />
                  ))}
                </VkCard>
              )}
            </>
          )}
        </>
      )}
    </Panel>
  );
};
