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
  Caption, Text, Card as VkCard, Input, Checkbox, Box,
  Textarea, Header, IconButton, Chip,
} from '@vkontakte/vkui';
import {
  Icon56DocumentOutline, Icon28EditOutline, Icon28AttachOutline,
  Icon24Filter,
} from '@vkontakte/icons';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useAppStore } from '@/shared/lib/store';
import { useToast } from '@/shared/components/Toast';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { SubmissionReviewCard } from '@/pages/dashboard/components/feed';
import { HomeworkFilterModal } from '@/pages/homework/HomeworkFilterModal';
import { SectionTitle, TeacherHwCard, RightPill } from '@/shared/components/TeacherHomeworkCards';
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
              <RightPill h={meta} />
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
          onSaved={() => { load(); onListChanged(); }}
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
  const [openId, setOpenId] = React.useState<number | null>(null);
  // Фильтры класс/предмет: Set-ы значений; пустой Set = «все».
  const [filters, setFilters] = React.useState({ batches: new Set<string>(), subjects: new Set<string>() });
  const [filtersOpen, setFiltersOpen] = React.useState(false);

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
    // Логика разделов (согласована 2026-09-17, мокап): непересекающиеся
    // состояния. Выданные — ответов ещё нет; К проверке — есть ответы,
    // не все приняты (в т.ч. возвращённые на доработку); Проверено —
    // все полученные ответы приняты либо приём закрыт.
    return {
      review: filtered.filter(h => h.state === 'publish' && h.submitted > 0),
      issued: filtered.filter(h => h.state === 'publish' && h.submitted === 0),
      checked: filtered.filter(h => h.state === 'finish'),
    };
  }, [items, filters]);

  const allHidden = groups.review.length + groups.issued.length + groups.checked.length === 0;

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
              {/* Чипы активного фильтра слева, кнопка-фильтр справа
                  (мокап teacher-homework-mockup.html). Обёртка flex:1 —
                  чтобы кнопка стояла справа и при пустых чипах. */}
              <Div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, paddingBottom: 8 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <FilterChips
                    active={{
                      batches: [...filters.batches],
                      subjects: [...filters.subjects],
                    }}
                    onRemove={removeFilter}
                    onReset={resetFilters}
                  />
                </div>
                <IconButton
                  label="Фильтры"
                  aria-expanded={filtersOpen}
                  style={filterActive ? {
                    color: 'var(--vkui--color_background_accent)',
                    flexShrink: 0,
                  } : { flexShrink: 0 }}
                  onClick={() => setFiltersOpen(true)}
                >
                  <Icon24Filter />
                </IconButton>
              </Div>

              {allHidden ? (
                <Placeholder
                  icon={<Icon56DocumentOutline />}
                  title="Нет заданий"
                >
                  <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
                    {filterActive
                      ? 'Нет заданий по выбранным фильтрам.'
                      : 'Задайте ДЗ из журнала урока.'}
                  </Caption>
                </Placeholder>
              ) : (
                // .inner мокапа: 12px от краёв экрана; заголовки и карточки
                // живут в одном контейнере (карточка сама даёт margin 6 0).
                <Box paddingInline={12} paddingBlockEnd={12}>
                  {/* Разделы одной лентой: цветной заголовок 20px + счётчик
                      (мокап), пустые разделы не рисуются. Порядок: К проверке
                      (ближайшее действие) -> Выданные -> Проверено. */}
                  {groups.review.length > 0 && (
                    <>
                      <SectionTitle first tone="review" title="К проверке" count={groups.review.length} />
                      {groups.review.map(h => (
                        <TeacherHwCard key={h.id} h={h} showFaculty={showFaculty} onOpen={setOpenId} />
                      ))}
                    </>
                  )}
                  {groups.issued.length > 0 && (
                    <>
                      <SectionTitle tone="issued" title="Выданные" count={groups.issued.length} />
                      {groups.issued.map(h => (
                        <TeacherHwCard key={h.id} h={h} showFaculty={showFaculty} onOpen={setOpenId} />
                      ))}
                    </>
                  )}
                  {groups.checked.length > 0 && (
                    <>
                      <SectionTitle tone="checked" title="Проверено" count={groups.checked.length} />
                      {groups.checked.map(h => (
                        <TeacherHwCard key={h.id} h={h} showFaculty={showFaculty} onOpen={setOpenId} />
                      ))}
                    </>
                  )}
                </Box>
              )}
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
