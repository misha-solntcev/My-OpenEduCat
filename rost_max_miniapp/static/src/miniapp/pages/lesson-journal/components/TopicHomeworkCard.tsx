// Карточка «Тема · ДЗ» в журнале урока. Три состояния ДЗ:
//  1. черновик (state=draft) — можно писать, скрепка в поле, кнопка «Выдать»;
//  2. выдано (state=publish) — только чтение + «Редактировать» и «Проверить N»;
//  3. правка выданного — «Отмена» и «Сохранить».
// Публикует учитель явно: автосинк создаёт задание в draft, ученики его не
// видят, срок и пост в канал считаются в момент «Выдать».
// Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { Box, Flex, Text, Caption, Input, Button, Checkbox, Counter } from '@vkontakte/vkui';
import { Icon24ChevronDown, Icon24ChevronUp } from '@vkontakte/icons';
import { AttachField, HW_MAX_HEIGHT } from '@/shared/components/AttachField';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { apiPost, fileToBase64 } from '@/shared/lib/api';
import type { LessonInfo } from '@/shared/lib/types';

/**
 * Хук прикрепления материалов к ДЗ урока. Отдаёт пропы, которые надо
 * развести на кнопку-скрепку (она живёт в поле ввода, а не отдельной
 * строкой). Саму кнопку этот компонент НЕ рисует — иначе в поле ввода
 * оказалось бы две скрепки.
 */
const useLessonMaterials = (
  lessonId: number,
  onAssignmentCreated: (id: number) => void,
  onChanged?: () => void,
) => {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const addFiles = async (list: FileList | null) => {
    if (!list || list.length === 0) return;
    const MAX_MB = 10;
    const payload = [];
    for (const f of Array.from(list)) {
      const goodType = f.type.startsWith('image/') || f.type === 'application/pdf';
      if (goodType && f.size <= MAX_MB * 1024 * 1024) {
        try {
          payload.push({ filename: f.name, mimetype: f.type, b64: await fileToBase64(f) });
        } catch { /* пропускаем нечитаемый файл */ }
      }
    }
    if (payload.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiPost<{
        success?: boolean;
        error?: string;
        assignment_id?: number;
      }>(`/rost_max/api/lesson/${lessonId}/materials`, { files: payload });
      if (res.error || !res.assignment_id) {
        setError(res.error || 'Не удалось прикрепить');
      } else {
        onAssignmentCreated(res.assignment_id);
        // Задание уже существовало — onAssignmentCreated лишь закрепляет id,
        // список превью надо перечитать.
        if (onChanged) onChanged();
      }
    } catch {
      setError('Не удалось прикрепить');
    }
    setBusy(false);
  };

  return {
    /* Тип AttachProps — общий для скрепки: IconButton, у которого нет
       loading, поэтому хук отдаёт onClick + disabled. */
    attachProps: {
      /* IconButton не умеет loading — на время загрузки гасим скрепку. */
      disabled: busy,
      onClick: (e: React.MouseEvent) => {
        e.stopPropagation();
        fileInputRef.current?.click();
      },
    },
    onChanged,
        error,
        hiddenInput: (
      <input
        key="lesson-materials-input"
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        multiple
        style={{ display: 'none' }}
        onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
      />
    ),
  };
};

/** Дата ISO -> «29 сен» (или «29 сен 2026», если год другой). */
const formatDue = (iso: string): string => {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  const base = `${d.getDate()} ${months[d.getMonth()]}`;
  const now = new Date();
  return d.getFullYear() === now.getFullYear() ? base : `${base} ${d.getFullYear()}`;
};

interface TopicHomeworkCardProps {
  lesson: LessonInfo;
  lessonId: number;
  canEdit: boolean;
  onTopicChange: (topic: string) => void;
  onHomeworkChange: (homework: string) => void;
  onAnswerRequiredChange: (value: boolean) => void;
  onAssignmentCreated: (id: number) => void;
  /** Сохранить несохранённые правки перед действием с ДЗ (выдать/отозвать).
   *  Вызывается ДО запроса на сервер: без этого «Выдать» опубликовал бы
   *  прежний серверный текст, а только что набранный остался бы в поле. */
  onBeforeHwAction?: () => Promise<void> | void;
  /** Перечитать журнал после выдачи/отзыва/удаления — вернёт новое
   *  homework_state и срок с сервера. */
  onReload?: () => void;
  /** Вход на экран «Заданий» с фильтром по этому уроку. Оценки за ДЗ в
   *  журнале не ставятся — они живут в задании, поэтому карточка ведёт туда.
   *  Счётчик — сколько заданий к проверке (0 тоже показываем явно). */
  onCheckHomework?: () => void;
}

/**
 * Карточка «Тема · ДЗ», свёрнутая: превью одной строкой, раскрытие по тапу.
 * В раскрытом виде — тема и ДЗ полями ввода (черновик) либо текстом
 * (выдано), плюс действия.
 */
export const TopicHomeworkCard: React.FC<TopicHomeworkCardProps> = ({
  lesson,
  lessonId,
  canEdit,
  onTopicChange,
  onHomeworkChange,
  onAnswerRequiredChange,
  onAssignmentCreated,
  onBeforeHwAction,
  onReload,
  onCheckHomework,
}) => {
  const [expanded, setExpanded] = React.useState(false);
  const [materialsRev, setMaterialsRev] = React.useState(0);
  const [publishing, setPublishing] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);
  // Правка выданного задания: явный режим, показывается по «Редактировать».
  const [editing, setEditing] = React.useState(false);
  const { attachProps, hiddenInput, error: hwError } = useLessonMaterials(
    lessonId, onAssignmentCreated, () => setMaterialsRev(v => v + 1),
  );

  const hwState = lesson.homework_state || '';
  const isPublished = hwState === 'publish' || hwState === 'finish';
  const isDraft = hwState === 'draft';
  // Поле ввода показываем в черновике, когда задания ещё нет, и в режиме
  // правки выданного. В выданном состоянии — только чтение.
  const showHwEditor = canEdit && (!isPublished || editing);
  const canCheck = Boolean(onCheckHomework) && isPublished;
  const toReview = lesson.hw_to_review ?? 0;
  const dueText = formatDue(lesson.homework_due || '');

  const hwAttachProps = showHwEditor ? attachProps : null;

  const runHwAction = async (path: string, okMessage?: string) => {
    setPublishing(true);
    setActionError(null);
    try {
      // Сначала сохраняем набранное: иначе «Выдать» опубликовало бы прежний
      // серверный текст, а свежий остался бы только в поле.
      if (onBeforeHwAction) await onBeforeHwAction();
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/lesson/${lessonId}/hw/${path}`, {},
      );
      if (res.error || !res.success) {
        setActionError(res.error || 'Не удалось выполнить действие');
      } else {
        setEditing(false);
        if (okMessage) setActionError(null);
        if (onReload) onReload();
      }
    } catch {
      setActionError('Не удалось выполнить действие');
    }
    setPublishing(false);
  };

  /* «Выдать» — публикация черновика. Кнопка есть на каждом уроке (Миша:
     «должна быть всегда»), но без текста и без фото нажимать нечего —
     поэтому disabled, а не спрятана: место не прыгает, когда учитель
     начинает вписывать ДЗ. Перед запросом onBeforeHwAction сохраняет
     набранное — и заодно создаёт задание, если его ещё нет. */
  const hasHwContent = Boolean(
    (lesson.homework || '').trim() || lesson.homework_assignment_id);
  const publishButton = !isPublished ? (
    <Button
      size="l"
      mode="primary"
      appearance="accent"
      disabled={!hasHwContent}
      loading={publishing}
      onClick={e => { e.stopPropagation(); runHwAction('publish'); }}
    >
      Выдать
    </Button>
  ) : null;

  /* Проверка ДЗ: оценки за ДЗ в журнале не ставятся — они живут в задании,
     поэтому отсюда один вход на готовый экран «Заданий», отфильтрованный по
     этому уроку (предмет + класс). Показываем только у ВЫДАННОГО задания:
     в черновике сдач быть не может, «Проверить 0» был бы шумом. Счётчик —
     внутри кнопки, поэтому содержимое обёрнуто в Flex: vkuiCounter__host
     это display:flex, и рядом с инлайновым текстом он роняет строку.
     mode="contrast" — белым по синему, иначе не читается. */
  const checkButton = canCheck ? (
    <Button
      size="l"
      mode="primary"
      appearance="accent"
      onClick={e => { e.stopPropagation(); onCheckHomework!(); }}
    >
      <Flex align="center" gap={8}>
        <span>Проверить</span>
        <Counter size="s" mode="contrast">{toReview}</Counter>
      </Flex>
    </Button>
  ) : null;

  const hasContent = Boolean(lesson.topic || lesson.homework || lesson.homework_assignment_id);
  const previewTopic = lesson.topic || 'Тема не указана';
  const previewHw = lesson.homework
    ? `ДЗ: ${lesson.homework}`
    : (lesson.homework_assignment_id ? 'ДЗ: фото/материалы' : 'ДЗ не задано');

  // Пустая тема — пунктирная рамка без заливки, тень elevation3 — заметно
  // плотнее карточек учеников (elevation2), чтобы зона выделялась;
  // заполненная — белая карточка с той же elevation3.
  const cardStyle: React.CSSProperties = hasContent || expanded
    ? {
        backgroundColor: 'var(--vkui--color_background_content)',
        borderRadius: 'var(--vkui--size_card_border_radius--regular)',
        boxShadow: 'var(--vkui--elevation3)',
        cursor: 'pointer',
      }
    : {
        backgroundColor: 'transparent',
        borderRadius: 'var(--vkui--size_card_border_radius--regular)',
        border: '1.5px dashed var(--vkui--color_icon_secondary)',
        boxShadow: 'var(--vkui--elevation3)',
        cursor: 'pointer',
      };

  return (
    <Box
      padding="m"
      onClick={() => setExpanded(v => !v)}
      style={cardStyle}
    >
      {!expanded ? (
        /* Свёрнуто: превью темы и ДЗ, шеврон раскрытия и кнопка у ПРАВОГО
           края. Кнопка не растянута, поэтому текст превью ужимается эллипсом,
           а не выталкивает её за экран (minWidth: 0 у колонки превью —
           иначе flex не даёт сжать текст). */
        <Flex align="center" gap={10}>
          <Text weight="2" style={{ flexShrink: 0 }}>📘</Text>
          <Flex direction="column" style={{ flexGrow: 1, minWidth: 0 }}>
            <Text weight="2" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {previewTopic}
            </Text>
            <Caption level="1" style={{
              color: 'var(--vkui--color_text_secondary)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {previewHw}
            </Caption>
          </Flex>
          <Icon24ChevronDown style={{ flexShrink: 0, color: 'var(--vkui--color_icon_secondary)' }} />
          {checkButton}
        </Flex>
      ) : (
        <Flex direction="column" gap={12} onClick={e => e.stopPropagation()}>
          <Flex direction="column" gap={4}>
            <Caption level="1" weight="2" style={{ color: 'var(--vkui--color_text_secondary)' }}>
              ТЕМА
            </Caption>
            {canEdit ? (
              <Input
                value={lesson.topic}
                onChange={e => onTopicChange(e.target.value)}
                placeholder="Например: Квадратные уравнения"
                aria-label="Тема урока"
              />
            ) : (
              <Text>{lesson.topic || '—'}</Text>
            )}
          </Flex>

          <Flex direction="column" gap={4}>
            <Flex align="center" justify="space-between">
              <Caption level="1" weight="2" style={{ color: 'var(--vkui--color_text_secondary)' }}>
                ДОМАШНЕЕ ЗАДАНИЕ
              </Caption>
              {/* Подпись состояния. Второй строкой ничего не пишем: учитель
                  и так видит, что нажал не ту кнопку, а кнопка «Выдать»
                  рядом уже всё объясняет. */}
              {isDraft && (
                <Caption level="1" weight="2" style={{ color: 'var(--vkui--color_text_accent_themed)' }}>
                  Черновик
                </Caption>
              )}
              {isPublished && (
                <Caption level="1" weight="2" style={{ color: 'var(--vkui--color_text_positive)' }}>
                  Выдано
                </Caption>
              )}
            </Flex>
            {showHwEditor ? (
              /* Поле ДЗ со скрепкой: общий компонент AttachField. Скрепка
                 штатная, слотом `after` — VKUI сам сдвигает текст, поэтому
                 relative/absolute и paddingRight больше не нужны. */
              <AttachField
                value={lesson.homework}
                onChange={onHomeworkChange}
                placeholder="Например: §14, №412–418 или фото доски"
                ariaLabel="Домашнее задание"
                attachProps={hwAttachProps ?? {}}
                hiddenInput={hiddenInput}
                maxHeight={HW_MAX_HEIGHT}
              />
            ) : (
              /* Выданное ДЗ — только чтение. Случайная правка текста после
                 выдачи переписала бы пост в канале у всех учеников с
                 пометкой «(изменено)» — поэтому текст тут не полем. */
              <Text>{lesson.homework || '—'}</Text>
            )}
            {showHwEditor && !isPublished && lesson.homework && !lesson.homework_assignment_id && (
              <Caption level="1" style={{ color: 'var(--vkui--color_text_secondary)' }}>
                При сохранении создастся черновик — ученики увидят задание после «Выдать»
              </Caption>
            )}
            {/* Срок — считается при публикации, у черновика его нет. */}
            {isPublished && dueText && (
              <Caption level="1" style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Срок сдачи — {dueText}
              </Caption>
            )}
          </Flex>

          {showHwEditor && lesson.homework && (
            <Checkbox
              checked={lesson.homework_answer_required}
              onChange={e => onAnswerRequiredChange(e.target.checked)}
            >
              <Caption level="1" style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Требуется ответ при сдаче
              </Caption>
            </Checkbox>
          )}

          {/* Превью прикреплённого — сетка миниатюр, как в мессенджерах. Слова
              «Материалы» здесь нет: скрепка и так в поле ввода, а это
              результат. key с materialsRev — перечитывает список после
              прикрепления через скрепку. В выданном состоянии скрепки нет,
              но превью и удаление (для учителя) остаются. */}
          {lesson.homework_assignment_id && (showHwEditor || isPublished) && (
            <MaterialsEditor
              key={`${lesson.homework_assignment_id}:${materialsRev}`}
              assignmentId={lesson.homework_assignment_id}
              showAttachButton={false}
              /* Удалили последний фото — задание снесено на сервере,
                 перечитываем урок: вернётся пустой текст без задания. */
              onAssignmentRemoved={onReload}
            />
          )}
          {(showHwEditor && hwError) && (
            <Caption level="1" style={{ color: 'var(--vkui--color_text_negative)' }}>
              {hwError}
            </Caption>
          )}
          {actionError && (
            <Caption level="1" style={{ color: 'var(--vkui--color_text_negative)' }}>
              {actionError}
            </Caption>
          )}
          {hiddenInput}

          {/* Действия. Раскрытие/сворачивание — шевроном в превью, отдельной
              кнопки «Свернуть» нет: она дублировала шеврон и выглядела ещё
              одним полем формы.

              Раскладка по режимам: пара «Редактировать» + «Проверить N» — по
              центру рядом (Миша), это единственный режим с двумя кнопками
              разного веса, и space-between раздвигал их по краям карточки.
              Остальное — «Выдать» слева, «Отмена» рядом с ним: единственная
              кнопка в ряду, центрировать её незачем. */}
          <Flex
            align="center"
            gap={8}
            justify={isPublished && !editing ? 'center' : 'start'}
          >
            {/* Черновик: единственное действие — «Выдать». */}
            {publishButton}
            {/* Правка выданного: «Отмена» возвращает в чтение. */}
            {isPublished && editing && (
              <Button
                size="l"
                mode="secondary"
                appearance="neutral"
                onClick={() => setEditing(false)}
              >
                Отмена
              </Button>
            )}
            {/* Выданное в режиме чтения: «Редактировать» тише, «Проверить N»
                главная. */}
            {isPublished && !editing && (
              <Button
                size="l"
                mode="secondary"
                appearance="accent"
                onClick={() => setEditing(true)}
              >
                Редактировать
              </Button>
            )}
            {isPublished && !editing && checkButton}
          </Flex>
        </Flex>
      )}
      {!hasContent && !expanded && (
        <Caption level="1" style={{ color: 'var(--vkui--color_text_accent_themed)', marginTop: 4 }}>
          Нажмите, чтобы заполнить
        </Caption>
      )}
    </Box>
  );
};
