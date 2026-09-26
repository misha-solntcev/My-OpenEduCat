/**
 * Вкладка «Задания» учителя/админа (по образцу Google Classroom).
 *
 * Сегменты: «Проверить» (есть сдачи submit) / «Активные» (publish) /
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
  Panel, PanelHeader, PanelHeaderBack, PanelHeaderContent, Div, Spinner, Button,
  Caption, Text, Card as VkCard, Input, Checkbox, Box,
  Textarea, IconButton, Chip,
} from '@vkontakte/vkui';
import {
  Icon28EditOutline, Icon28AttachOutline, Icon28FlashOutline,
  Icon24Filter, Icon24ListCheckOutline,
} from '@vkontakte/icons';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useAppStore } from '@/shared/lib/store';
import { useToast } from '@/shared/components/Toast';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { ReviewQueue } from '@/shared/components/ReviewQueue';
import { BulkReviewSheet } from '@/shared/components/BulkReviewSheet';
import { SubjectAvatar } from '@/shared/components/SubjectIcon';
import { HomeworkFilterModal } from '@/pages/homework/HomeworkFilterModal';
import { AccentSegmentedControl } from '@/shared/components/AccentSegmentedControl';
import { TeacherHwCard, RightPill } from '@/shared/components/TeacherHomeworkCards';
import type {
  TeacherHomeworkItem, TeacherHomeworkResponse, HomeworkSubmissionsResponse,
} from '@/shared/lib/types';

const MONTHS = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн',
  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

type StatusKey = 'review' | 'issued' | 'checked';

/** Сегмент-контрол статусов + текст пустого списка каждого статуса. */
const SEGMENTS: { key: StatusKey; title: string; empty: string }[] = [
  { key: 'review', title: 'Проверить', empty: 'Нет работ для проверки' },
  { key: 'issued', title: 'Выдано', empty: 'Нет выданных заданий без ответов' },
  { key: 'checked', title: 'Проверено', empty: 'Проверенных заданий пока нет' },
];

const fmtDue = (due: string): string => {
  if (!due) return '';
  const d = new Date(due);
  if (isNaN(d.getTime())) return due;
  return `до ${d.getDate()} ${MONTHS[d.getMonth()]}`;
};

/** Строка чипов активного фильтра + кнопка «Сбросить» (мокап). */
const FilterChips: React.FC<{
  active: { batches: string[]; subjects: string[] };
  onRemove: (kind: 'batch' | 'subject', v: string) => void;
  onReset: () => void;
}> = ({ active, onRemove, onReset }) => {
  const chips = [
    ...active.batches.map(v => ({ kind: 'batch' as const, v })),
    ...active.subjects.map(v => ({ kind: 'subject' as const, v })),
  ];
  if (chips.length === 0) return null;
  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', alignItems: 'center',
      gap: 6, minWidth: 0, flex: 1,
    }}>
      {chips.map(({ kind, v }) => (
        <Chip
          key={`${kind}:${v}`}
          removable
          onRemove={() => onRemove(kind, v)}
          aria-label={`Убрать фильтр: ${v}`}
        >
          {v}
        </Chip>
      ))}
      <Button
        mode="tertiary"
        size="s"
        appearance="accent"
        onClick={onReset}
      >
        Сбросить
      </Button>
    </div>
  );
};

/** Экран правки задания (шторка-карточка в потоке страницы). */
const EditHomeworkCard: React.FC<{
  h: TeacherHomeworkItem;
  onClose: () => void;
  onSaved: () => void;
}> = ({ h, onClose, onSaved }) => {
  const addToast = useToast();
  const [task, setTask] = React.useState(h.task);
  const [topic, setTopic] = React.useState(h.topic || '');
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
      const payload: Record<string, unknown> = { task: task.trim() };
      if (topic.trim() !== (h.topic || '')) {
        payload.topic = topic.trim();
      }
      if (dueDate !== (h.due || '').slice(0, 10)) {
        payload.due = `${dueDate} 23:59:00`;
      }
      if (answerRequired !== h.answer_required) {
        payload.answer_required = answerRequired;
      }
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/homework/${h.id}/edit`, payload);
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

        <Caption style={{
          color: 'var(--vkui--color_text_secondary)', display: 'block',
          marginBottom: 4,
        }}>
          Тема урока
        </Caption>
        <Input
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="Тема урока"
          aria-label="Тема урока"
          style={{ marginBottom: 8 }}
        />

        <Caption style={{
          color: 'var(--vkui--color_text_secondary)', display: 'block',
          marginBottom: 4,
        }}>
          Текст задания
        </Caption>
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
}> = ({ assignmentId, onBack, onListChanged }) => {
  const addToast = useToast();
  const [data, setData] = React.useState<HomeworkSubmissionsResponse | null>(null);
  const [meta, setMeta] = React.useState<TeacherHomeworkItem | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [editing, setEditing] = React.useState(false);
  const [busyFinish, setBusyFinish] = React.useState(false);
  // Шторка массовых действий («Весь класс») — как молния в журнале урока.
  const [bulkOpen, setBulkOpen] = React.useState(false);

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
      <PanelHeader
        before={<PanelHeaderBack onClick={onBack} />}
        after={meta && data && (
          <IconButton
            label="Массовые действия: принять всем, оценка всем"
            onClick={() => setBulkOpen(true)}
          >
            <Icon28FlashOutline />
          </IconButton>
        )}
      >
        <PanelHeaderContent
          before={meta && (
            <SubjectAvatar subject={meta.subject} color={meta.subject_color} size={30} />
          )}
          subtitle={meta?.faculty || undefined}
        >
          {meta ? `${meta.subject} · ${meta.batch}` : 'Задание'}
        </PanelHeaderContent>
      </PanelHeader>

      {meta && (
        <VkCard mode="shadow" style={{ margin: '8px 8px 0', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px' }}>
            {/* мокап D: [иконка ДЗ] [задание / тема-срок] — иконка ДЗ (чек-лист
                на синем тинте) отличается от палитры предметов (FontAwesome). */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <span style={{
                width: 38, height: 38, borderRadius: 10, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--vkui--color_background_secondary)',
                border: '1px solid var(--vkui--color_separator_primary)',
                color: 'var(--vkui--color_text_accent)',
              }}>
                <Icon24ListCheckOutline width={20} height={20} />
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Text weight="2" style={{
                  color: 'var(--vkui--color_text_primary)', display: 'block',
                  whiteSpace: 'pre-wrap', overflowWrap: 'anywhere',
                }}>
                  {meta.task}
                </Text>
                <Caption style={{
                  color: 'var(--vkui--color_text_secondary)', display: 'block',
                  marginTop: 4,
                }}>
                  {[
                    meta.topic ? `Тема: ${meta.topic}` : '',
                    fmtDue(meta.due),
                    meta.answer_required ? 'требуется ответ' : '',
                    meta.state === 'finish' ? 'приём завершён' : '',
                  ].filter(Boolean).join(' · ')}
                </Caption>
              </div>
              <RightPill h={meta} />
            </div>

            {/* мокап D: синий прогресс проверки (submitted с оценкой неизвестен,
                поэтому «принято» = total - submit - change - none/draft из counts) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10 }}>
              <div style={{
                flex: 1, height: 4, borderRadius: 2, overflow: 'hidden',
                background: 'var(--vkui--color_background_secondary)',
              }}>
                <div style={{
                  height: '100%', borderRadius: 2,
                  width: `${meta.total > 0
                    ? Math.min(100, Math.round(100 * meta.accepted / meta.total))
                    : 0}%`,
                  background: 'var(--vkui--color_text_accent)',
                }} />
              </div>
              <Caption style={{ whiteSpace: 'nowrap', color: 'var(--vkui--color_text_secondary)' }}>
                <Text style={{ color: 'var(--vkui--color_text_primary)', fontWeight: 600 }}>
                  {meta.accepted} из {meta.total}
                </Text>
                {' '}проверено
              </Caption>
            </div>

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

            {/* Кнопки: единый стиль (outline), равная ширина, текст по центру. */}
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <Button
                size="s" mode="outline" stretched
                before={<Icon28EditOutline width={16} height={16} />}
                disabled={editing}
                onClick={() => setEditing(true)}
              >
                Редактировать
              </Button>
              {meta.state === 'publish' ? (
                <Button
                  size="s" mode="outline" appearance="negative" stretched
                  loading={busyFinish} onClick={toggleFinish}
                >
                  Завершить приём
                </Button>
              ) : (
                <Button
                  size="s" mode="outline" stretched
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
          onSaved={() => { load(); onListChanged(); }}
        />
      )}

      {data && (
        <ReviewQueue
          submission={data}
          onReview={async (subId, action, note, mark, studentId, mark2) => {
              try {
                // subId === null — приём без сдачи (ответ устно/в тетради):
                // создаёт строку сдачи сразу с итоговым состоянием.
                const url = subId === null
                  ? `/rost_max/api/homework/${data!.assignment.id}/review_student`
                  : `/rost_max/api/homework/submission/${subId}/review`;
                const payload = subId === null
                  ? { student_id: studentId, action, teacher_note: note, mark, mark_2: mark2 }
                  : { action, teacher_note: note, mark, mark_2: mark2 };
                const res = await apiPost<{ success?: boolean; error?: string }>(url, payload);
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
        />
      )}
      {meta && (
        <BulkReviewSheet
          assignmentId={meta.id}
          open={bulkOpen}
          onClose={() => setBulkOpen(false)}
          onApplied={() => { addToast('Принято у всего класса', 'success'); load(); onListChanged(); }}
          onError={msg => addToast(msg, 'error')}
        />
      )}
    </Panel>
  );
};

export const TeacherHomeworkPage: React.FC<{ id: string }> = ({ id }) => {
  const addToast = useToast();
  const [items, setItems] = React.useState<TeacherHomeworkItem[] | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [openId, setOpenId] = React.useState<number | null>(null);
  // Фильтры класс/предмет: Set-ы значений; пустой Set = «все».
  const [filters, setFilters] = React.useState({ batches: new Set<string>(), subjects: new Set<string>() });
  const [filtersOpen, setFiltersOpen] = React.useState(false);
  // Активный сегмент статуса (сегмент-контрол как в ReviewQueue).
  const [status, setStatus] = React.useState<StatusKey>('review');

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
    // Фильтр: внутри группы ИЛИ, между группами И. Пустой Set = «все».
    const pass = (h: TeacherHomeworkItem) =>
      (!filters.batches.size || filters.batches.has(h.batch))
      && (!filters.subjects.size || filters.subjects.has(h.subject));
    const filtered = all.filter(pass);
    return {
      review: filtered.filter(h => h.state === 'publish' && h.to_review > 0),
      issued: filtered.filter(h => h.state === 'publish' && h.submitted === 0 && h.to_review === 0),
      checked: filtered.filter(h => h.state === 'finish'
        || (h.state === 'publish' && h.submitted > 0 && h.to_review === 0)),
    };
  }, [items, filters]);

  const filterActive = filters.batches.size > 0 || filters.subjects.size > 0;

  const removeFilter = (kind: 'batch' | 'subject', v: string) => {
    setFilters(prev => {
      const key = kind === 'batch' ? 'batches' : 'subjects';
      const next = new Set(prev[key]);
      next.delete(v);
      return { ...prev, [key]: next };
    });
  };

  const resetFilters = () =>
    setFilters({ batches: new Set<string>(), subjects: new Set<string>() });

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
              <Div style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '14px 18px',
                background: 'var(--vkui--color_background_content)',
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text Component="h1" weight="2" style={{ fontSize: 23, letterSpacing: '-0.6px', margin: 0 }}>
                    Задания
                  </Text>
                </div>
                <IconButton
                  label="Фильтры"
                  aria-expanded={filtersOpen}
                  style={{
                    color: filterActive ? 'var(--vkui--color_text_accent)' : 'var(--vkui--color_text_secondary)',
                    flexShrink: 0, borderRadius: 12,
                    border: '1px solid var(--vkui--color_separator_primary)',
                    background: filterActive ? 'var(--vkui--color_background_secondary)' : undefined,
                  }}
                  onClick={() => setFiltersOpen(true)}
                >
                  <Icon24Filter />
                </IconButton>
              </Div>

              {filterActive && (
                <Div style={{ padding: '10px 16px', background: 'var(--vkui--color_background_content)' }}>
                  <FilterChips
                    active={{ batches: [...filters.batches], subjects: [...filters.subjects] }}
                    onRemove={removeFilter}
                    onReset={resetFilters}
                  />
                </Div>
              )}

              <Box paddingInline={12} paddingBlockStart={4} paddingBlockEnd={22}>
                {/* сегмент-контрол статусов (общий AccentSegmentedControl). */}
                <div style={{ paddingTop: 4, paddingBottom: 10 }}>
                  <AccentSegmentedControl
                    aria-label="Статусы заданий"
                    value={status}
                    onChange={setStatus}
                    options={SEGMENTS.map(({ key, title }) => ({
                      value: key, title, count: groups[key].length,
                    }))}
                  />
                </div>

                {groups[status].length > 0 ? groups[status].map(h => (
                  <TeacherHwCard key={h.id} h={h} showFaculty={showFaculty} onOpen={setOpenId} />
                )) : (
                  <Caption style={{ padding: '12px 14px', color: 'var(--vkui--color_text_secondary)' }}>
                    {filterActive ? 'Нет заданий по выбранным фильтрам' : SEGMENTS.find(s => s.key === status)!.empty}
                  </Caption>
                )}
              </Box>
            </>
          )}
        </>
      )}

      {/* Шторка фильтров: экран задания (openId) и список живут в одной
          Panel, модалка объявлена рядом с ними и доступна в обоих
          состояниях (VKUI ModalPage рендерится в AppRoot-портал). */}
      <HomeworkFilterModal
        open={filtersOpen}
        items={items || []}
        value={filters}
        onClose={() => setFiltersOpen(false)}
        onApply={f => {
          setFilters(f);
          setFiltersOpen(false);
        }}
      />
    </Panel>
  );
};
