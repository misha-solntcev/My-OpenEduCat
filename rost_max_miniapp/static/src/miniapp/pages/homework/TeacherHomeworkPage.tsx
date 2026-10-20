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
  IconButton,
} from '@vkontakte/vkui';
import {
  Icon28EditOutline, Icon28FlashOutline,
  Icon24ListCheckOutline,
} from '@vkontakte/icons';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useAppStore } from '@/shared/lib/store';
import { useToast } from '@/shared/components/Toast';
import { SaveBar } from '@/shared/components/SaveBar';
import { ExitBanner } from '@/shared/components/ExitBanner';
import { useViewerAxis, viewerChips, viewerFromDraft } from '@/shared/lib/viewerAxis';
import { TabHeader } from '@/shared/components/TabHeader';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { AttachField, HW_MAX_HEIGHT } from '@/shared/components/AttachField';
import { ReviewQueue } from '@/shared/components/ReviewQueue';
import { BulkReviewSheet } from '@/shared/components/BulkReviewSheet';
import { SubjectAvatar } from '@/shared/components/SubjectIcon';
import {
  ChipFilterModal, FilterChipRow, FilterIconButton,
} from '@/shared/components/ChipFilterModal';
import type { ChipFilters, ChipFilterSection } from '@/shared/components/ChipFilterModal';
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

// Строка чипов активного фильтра + «Сбросить» — общий FilterChipRow
// (мокап; ранее была локальной копией, вынесена для «Моих пар» Оценок).

/** Загрузка файлов в скрепку поля «Текст задания». Отдельный хук от
 *  useLessonMaterials в карточке урока: там endpoint /lesson/<id>/materials,
 *  здесь /homework/<id>/materials — оба делают append и требуют прав
 *  автора задания. Файлы уходят сразу, поэтому «Сохранить» их не ждёт. */
const useAttachFiles = (assignmentId: number) => {
  const addToast = useToast();
  const [busy, setBusy] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const addFiles = async (list: FileList | null) => {
    if (!list || list.length === 0) return;
    const MAX_MB = 10;
    const payload = [];
    for (const f of Array.from(list)) {
      const goodType = f.type.startsWith('image/') || f.type === 'application/pdf';
      if (goodType && f.size <= MAX_MB * 1024 * 1024) {
        try {
          const bin = await f.arrayBuffer();
          const b64 = btoa(String.fromCharCode(...new Uint8Array(bin)));
          payload.push({ filename: f.name, mimetype: f.type, b64 });
        } catch { /* пропускаем нечитаемый файл */ }
      }
    }
    if (payload.length === 0) {
      addToast('Только фото или PDF, до 10 МБ', 'error');
      return;
    }
    setBusy(true);
    try {
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/materials`, { files: payload });
      if (res.error || !res.success) {
        addToast(res.error || 'Не удалось прикрепить', 'error');
      } else {
        addToast('Прикреплено', 'success');
      }
    } catch {
      addToast('Не удалось прикрепить', 'error');
    }
    setBusy(false);
  };

  return {
    attachProps: {
      /* IconButton не умеет loading — на время загрузки гасим скрепку. */
      disabled: busy,
      onClick: (e: React.MouseEvent) => {
        e.stopPropagation();
        fileInputRef.current?.click();
      },
    },
    hiddenInput: (
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        multiple
        hidden
        onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
      />
    ),
  };
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
  const materials = useAttachFiles(h.id);

  const save = async () => {
    if (!task.trim()) {
      addToast('Текст задания не может быть пустым', 'error');
      return;
    }
    setBusy(true);
    try {
      const payload: Record<string, unknown> = { task: task.trim() };
      /* Тему шлём ТОЛЬКО у задания из журнала урока. У задания с ПК поля
         lesson_topic нет, и сервер вернул бы 409 на весь запрос — то есть
         из-за темы не сохранилось бы даже изменённое задание. Поле темы у
         такого задания и на форме скрыто. */
      if (h.sheet_id != null && topic.trim() !== (h.topic || '')) {
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
        <div style={{ marginBottom: 8 }}>
          <Text weight="2">Редактирование</Text>
        </div>

        {/* Задание без журнала урока (создано на ПК, родной модуль
            OpenEduCat): текст, срок, ответ и материалы правятся прямо в
            задании — сервер их принимает. Прячем только ТЕМУ УРОКА: у
            задания нет урока, значит нет и поля lesson_topic. Раньше здесь
            стояла заглушка «текст правится только в ПК-форме», которая
            закрывала форму целиком, хотя править было что. */}
        {h.sheet_id != null && (
          <>
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
          </>
        )}

        <Caption style={{
          color: 'var(--vkui--color_text_secondary)', display: 'block',
          marginBottom: 4,
        }}>
          Текст задания
        </Caption>
        {/* Поле со скрепкой — общий AttachField, как в полях ДЗ учителя и
            ответа ученика. Именно Input, а не Textarea: компонент один на
            все три места, а отступ под скрепкой задаёт сам VKUI (слот
            `after`). Раньше здесь был Textarea с ручным absolute — и
            paddingRight приходилось указывать в слоте textArea, вручную, в
            отличие от Input. Многострочность тут не нужна: длинный текст
            задания всё равно уходит в поле ДЗ урока. */}
        <div style={{ marginBottom: 8 }}>
          <AttachField
            value={task}
            onChange={setTask}
            placeholder="Текст домашнего задания"
            ariaLabel="Текст задания"
            attachProps={materials.attachProps}
            hiddenInput={materials.hiddenInput}
            disabled={busy}
            maxHeight={HW_MAX_HEIGHT}
          />
        </div>

        {/* Срок сдачи — подпись над полем, как «Тема урока» и «Текст задания»
            выше. Пробовал в одну строку (подпись слева, поле справа) — но
            подпись отдельной строкой стоит в этом списке везде, и
            одинаковая структура полей важнее экономии одного ряда. */}
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

        {/* Ряд кнопок: обе по центру и своей ширины, без stretched.
            Растянутая «Ок» на всю карточку читалась как поле формы, а не
            как действие — ровно то, чего договаривались избегать в действиях
            карточек ДЗ. Отдельно стоящая в углу «Отмена» тем более
            выпадала из логики: отмена действия — рядом с самим действием. */}
        <div style={{
          display: 'flex', gap: 8, marginTop: 8, justifyContent: 'center',
        }}>
          <Button
            size="l" appearance="accent"
            loading={busy} onClick={save}
          >
            Ок
          </Button>
          <Button
            size="l" mode="secondary" appearance="neutral"
            disabled={busy} onClick={onClose}
          >
            Отмена
          </Button>
        </div>
      </div>
    </VkCard>
  );
};

/** Экран одного задания: карточка + правка + сдачи.
 *  Оценки ДЗ (ДЗ 1/ДЗ 2 у принятых работ) живут в ЛОКАЛЬНОМ буфере здесь,
 *  а не в ReviewQueue: тап по оценке не ходит на сервер — один POST
 *  /save_marks по кнопке «Сохранить» или баннеру выхода (механика журнала
 *  урока). Раньше каждый тап у принятой работы сразу шёл POST /review и
 *  перезагружал два списка — на медленной сети тапы терялись. */
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

  // Буфер оценок (student_id -> оценка) + dirty-механика журнала урока.
  const [marks, setMarks] = React.useState<Record<number, number | null>>({});
  const [marks2, setMarks2] = React.useState<Record<number, number | null>>({});
  const [saving, setSaving] = React.useState(false);
  const [showExitBanner, setShowExitBanner] = React.useState(false);

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

  // Синк буфера с сервером. ВАЖНО: dirty считается ТОЛЬКО по строкам,
  // тронутым с момента загрузки (touchedRef): сравнивать весь буфер нельзя —
  // при входе буфер ещё пуст, и «пустой ≠ сохранённое на сервере» давало
  // ложный dirty, блокировало синк (кнопки выглядели пустыми при
  // сохранённых оценках), а «Сохранить» в этом состоянии затирало их нулями.
  const touchedRef = React.useRef<Set<string>>(new Set());
  const dirty = React.useMemo(() => (data ? data.students.some(s => {
    if (touchedRef.current.has(`${s.student_id}:1`)
      && (marks[s.student_id] ?? null) !== s.mark) return true;
    if (touchedRef.current.has(`${s.student_id}:2`)
      && (marks2[s.student_id] ?? null) !== s.mark_2) return true;
    return false;
  }) : false),
  [data, marks, marks2]);
  const dirtyRef = React.useRef(false);
  React.useEffect(() => { dirtyRef.current = dirty; }, [dirty]);
  React.useEffect(() => {
    if (!data || dirtyRef.current) return;
    setMarks(Object.fromEntries(data.students.map(s => [s.student_id, s.mark])));
    setMarks2(Object.fromEntries(data.students.map(s => [s.student_id, s.mark_2])));
    // Буфер совпадает с сервером — история правок закрыта.
    touchedRef.current = new Set();
  }, [data]);

  /** Тап по оценке — только буфер, без запроса. */
  const handleMarkChange = React.useCallback((studentId: number, which: 1 | 2, next: number | null) => {
    touchedRef.current.add(`${studentId}:${which}`);
    if (which === 1) {
      setMarks(prev => ({ ...prev, [studentId]: next }));
    } else {
      setMarks2(prev => ({ ...prev, [studentId]: next }));
    }
  }, []);

  const saveAll = async () => {
    if (saving || !data || !dirty) return;
    setSaving(true);
    try {
      // Шлём ВСЕ строки задания: у сдавших sub_id, у несдавших student_id —
      // бэк создаст сдачу state=accept (приём без сдачи, «устно/в тетради»).
      // Идемпотентно, один запрос. Пустые оценки у несдавших (sub_id=null,
      // mark=null) пропускаем — создавать сдачу ради пустой оценки нечего.
      const payload = data.students
        .filter(s => s.sub_id != null
          || (marks[s.student_id] ?? null) !== null
          || (marks2[s.student_id] ?? null) !== null)
        .map(s => ({
          sub_id: s.sub_id,
          student_id: s.student_id,
          mark: marks[s.student_id] ?? null,
          mark_2: marks2[s.student_id] ?? null,
        }));
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/save_marks`, { marks: payload });
      if (res.error) {
        addToast(res.error, 'error');
        return;
      }
      // Перезачитываем: буфер совпадёт с сервером, dirty погаснет, счётчики
      // на карточке обновятся.
      await load();
    } catch {
      addToast('Не удалось сохранить. Изменения сохранены локально, повторите позже.', 'error');
    } finally {
      setSaving(false);
    }
  };

  // Назад: с несохранёнными оценками — баннер «Сохранить изменения?».
  const handleBack = () => {
    if (dirty) {
      setShowExitBanner(true);
    } else {
      onBack();
    }
  };

  const exitSave = async () => {
    setShowExitBanner(false);
    await saveAll();
    onBack();
  };

  const exitDiscard = () => {
    setShowExitBanner(false);
    if (data) {
      setMarks(Object.fromEntries(data.students.map(s => [s.student_id, s.mark])));
      setMarks2(Object.fromEntries(data.students.map(s => [s.student_id, s.mark_2])));
    }
    onBack();
  };

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
        <PanelHeader before={<PanelHeaderBack onClick={handleBack} />} />
        <Div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spinner size="l" />
        </Div>
      </Panel>
    );
  }

  return (
    <Panel id="assignment-detail">
      <PanelHeader
        before={<PanelHeaderBack onClick={handleBack} />}
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

            {/* Материалы задания. Раньше здесь стояли ДВЕ скрепки: строка
                «Материалов: N» со значком и MaterialsEditor со своей кнопкой
                «Прикрепить». Обе не нужны — превью и кнопка добавления уже
                есть в MaterialsEditor, а счётчик рядом с ним только
                дублировал то, что видно по миниатюрам. */}
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
          marks={marks}
          marks2={marks2}
          onMarkChange={handleMarkChange}
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

      <SaveBar visible={dirty} saving={saving} onSave={saveAll} />
      <ExitBanner
        visible={showExitBanner}
        onClose={() => setShowExitBanner(false)}
        onSave={exitSave}
        onDiscard={exitDiscard}
        saving={saving}
      />
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

/** Фильтр-задание, приходящий из журнала урока (кнопка «Проверить ДЗ»). */
export interface TeacherHomeworkInitialFilter {
  batch: string;
  subject: string;
}

export const TeacherHomeworkPage: React.FC<{
  id: string;
  /** Стартовый фильтр из урока: показываем только его класс и предмет. */
  initialFilter?: TeacherHomeworkInitialFilter | null;
  /** Возврат в журнал урока. Задаётся ТОЛЬКО при входе из урока: во вкладке
   *  «Задания» кнопки «Назад» в шапке быть не должно, там и так таббар. */
  onBackToLesson?: () => void;
  onOpenProfile?: () => void;
}> = ({ id, initialFilter, onBackToLesson, onOpenProfile }) => {
  const addToast = useToast();
  // Ось «Кого смотрим» (свитч удалён — решение 2026-10-14): секция
  // ПЕРВАЯ в шторке, чип режима над лентой.
  const axis = useViewerAxis();
  const [items, setItems] = React.useState<TeacherHomeworkItem[] | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [openId, setOpenId] = React.useState<number | null>(null);
  // Фильтры класс/предмет: Set-ы значений; пустой Set = «все».
  const [filters, setFilters] = React.useState({ batches: new Set<string>(), subjects: new Set<string>() });
  const [filtersOpen, setFiltersOpen] = React.useState(false);
  // Зеркало черновика шторки (фасеты класс/предмет — как в «Моих парах»).
  const [sheetDraft, setSheetDraft] = React.useState<ChipFilters>({});
  // Активный сегмент статуса (сегмент-контрол как в ReviewQueue).
  const [status, setStatus] = React.useState<StatusKey>('review');

  // Вход из журнала урока: фильтр ставится РОВНО на каждое новое значение
  // initialFilter. Отдельно держим lastApplied — без него эффект не отличил бы
  // «учитель снял чипы руками» от «пришёл новый фильтр из урока»: фильтр
  // нулевой → setFilters на изменение не срабатывает, и вторая кнопка
  // «Проверить ДЗ» (другой класс) показала бы старый фильтр.
  const lastAppliedRef = React.useRef<string>('');
  // Флаг «сегмент ещё не выбран для текущего фильтра». Сегмент выбираем не
  // здесь, а отдельным эффектом по данным: на момент применения фильтра
  // items может быть ещё null (список грузится), и тогда любое решение
  // принималось бы вслепую.
  const pendingLessonSegmentRef = React.useRef(false);
  React.useEffect(() => {
    const f = initialFilter;
    if (!f || !f.batch || !f.subject) return;
    const key = `${f.batch}|${f.subject}`;
    if (lastAppliedRef.current === key) return;
    lastAppliedRef.current = key;
    setFilters({
      batches: new Set([f.batch]),
      subjects: new Set([f.subject]),
    });
    pendingLessonSegmentRef.current = true;
  }, [initialFilter?.batch, initialFilter?.subject]);

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

  const filterActive = filters.batches.size > 0 || filters.subjects.size > 0
    || Boolean(axis?.nonDefault);

  // Секции шторки: «Кого смотрим» ПЕРВОЙ (решение 2026-10-14), потом
  // Классы/Предметы с фасетным сужением (опции секции — по заданиям,
  // проходящим фильтры ДРУГИХ секций; выбранное не пропадает). Ось режима
  // на фасеты не влияет: список заданий от режима не зависит.
  const sections: ChipFilterSection[] = React.useMemo(() => {
    const itemsAll = items || [];
    const opts = (vals: string[], sel?: Set<string>): ChipFilterSection['options'] =>
      [...new Set([...vals, ...(sel?.size ? [...sel] : [])])]
        .sort((a, b) => a.localeCompare(b, 'ru', { numeric: true }))
        .map(v => ({ value: v }));
    const secBatches = itemsAll.filter(h =>
      !sheetDraft.subjects?.size || sheetDraft.subjects.has(h.subject));
    const secSubjects = itemsAll.filter(h =>
      !sheetDraft.batches?.size || sheetDraft.batches.has(h.batch));
    return [
      ...(axis ? [{ ...axis.section }] : []),
      { key: 'batches', header: 'Классы', options: opts(secBatches.map(h => h.batch), sheetDraft.batches) },
      { key: 'subjects', header: 'Предметы', options: opts(secSubjects.map(h => h.subject), sheetDraft.subjects) },
    ];
  }, [items, sheetDraft, axis]);

  // Выбор стартового сегмента при входе из урока — ПОСЛЕ того как список
  // загрузился и groups посчитан. Логика: кнопка «Проверить ДЗ» ведёт
  // проверять, поэтому если в фильтре есть что проверять — открываем
  // «Проверить». Жёстко ставить «Выдано» нельзя: на живых данных урока
  // 7 А Литература сегмент «Выдано» пуст (0 заданий), а «Проверить» — 3,
  // и учитель после тапа увидел бы пустую ленту и решил, что что-то сломано.
  // Если проверять нечего — «Выдано» (там лежат свежие невыданные).
  React.useEffect(() => {
    if (!pendingLessonSegmentRef.current) return;
    if (!items) return;                       // список ещё грузится — ждём
    pendingLessonSegmentRef.current = false;
    if (groups.review.length > 0) {
      setStatus('review');
    } else if (groups.issued.length > 0) {
      setStatus('issued');
    } else if (groups.checked.length > 0) {
      setStatus('checked');
    }
  }, [items, groups]);

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

  // Подзаголовок под «Задания»: при входе из урока показываем, по чему
  // список отфильтрован, — иначе учитель не понимает, почему тут пять
  // заданий вместо всех его. Если фильтр сняли чипами — подпись исчезает.
  const fromLesson = filterActive && initialFilter
    && [...filters.batches].includes(initialFilter.batch)
    && [...filters.subjects].includes(initialFilter.subject);

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
              {/* Шапка таба: аватар «кто смотрит» слева (Back из урока —
                  в его левом слоте), кнопка фильтра справа (решение
                  Миши 2026-10-14). */}
              <TabHeader
                title="Задания"
                before={onBackToLesson ? (
                  <PanelHeaderBack
                    onClick={onBackToLesson}
                    aria-label="Вернуться в журнал урока"
                  />
                ) : undefined}
                onOpenProfile={onOpenProfile}
                after={(
                  <FilterIconButton
                    active={filterActive}
                    expanded={filtersOpen}
                    onClick={() => {
                      setSheetDraft({
                        viewer: axis ? new Set([axis.value]) : new Set(),
                        batches: filters.batches,
                        subjects: filters.subjects,
                      });
                      setFiltersOpen(true);
                    }}
                  />
                )}
              />
              {fromLesson && initialFilter && (
                <Caption
                  level="3"
                  style={{ padding: '0 16px 4px', color: 'var(--vkui--color_text_secondary)' }}
                >
                  {`из урока: ${initialFilter.subject}, ${initialFilter.batch}`}
                </Caption>
              )}

              {/* Чипы над лентой: режим («Кого смотрим») всегда, класс/предмет —
                  при активном фильтре; «Сбросить» гасит всё, включая режим. */}
              {(filterActive || Boolean(axis)) && (
                <Div style={{ padding: '4px 16px 0' }}>
                  <FilterChipRow
                    chips={[
                      ...(viewerChips(axis)),
                      ...[...filters.batches].map(v => ({ kind: 'batch' as const, v })),
                      ...[...filters.subjects].map(v => ({ kind: 'subject' as const, v })),
                    ]}
                    onRemove={(kind, v) => {
                      if (kind === 'viewer') { axis?.apply('school'); return; }
                      removeFilter(kind as 'batch' | 'subject', v);
                    }}
                    onReset={() => {
                      resetFilters();
                      if (axis) axis.apply('school');
                    }}
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
          состояниях (VKUI ModalPage рендерится в AppRoot-портал).
          footerOrder='cancel-first' — единый порядок ОТМЕНА/ОК (решение
          Миши 2026-10-14). */}
      <ChipFilterModal
        open={filtersOpen}
        id="teacher-homework-filters"
        emptyText="Пока нет заданий — фильтровать нечего."
        sections={sections}
        value={sheetDraft}
        footerOrder="cancel-first"
        onClose={() => setFiltersOpen(false)}
        onDraftChange={setSheetDraft}
        onApply={f => {
          if (axis) axis.apply(viewerFromDraft(f.viewer, axis));
          setFilters({
            batches: f.batches ?? new Set<string>(),
            subjects: f.subjects ?? new Set<string>(),
          });
          setFiltersOpen(false);
        }}
      />
    </Panel>
  );
};
