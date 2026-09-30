// Прикрепление материалов ДЗ прямо из журнала урока. Кнопка видна ВСЕГДА,
// пока учитель может редактировать урок: текст ДЗ не обязателен — фото
// доски само создаёт задание (бэкенд: POST /lesson/<id>/materials).
// Когда задание уже есть — работаем с ним напрямую через MaterialsEditor.
// Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { Box, Flex, Text, Caption, Input, Button, Checkbox, Counter } from '@vkontakte/vkui';
import { Icon24ChevronDown, Icon24ChevronUp, Icon28AttachOutline } from '@vkontakte/icons';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { apiPost, fileToBase64 } from '@/shared/lib/api';
import type { LessonInfo } from '@/shared/lib/types';

/**
 * Хук прикрепления материалов к ДЗ урока. Отдаёт пропы, которые надо
 * развести на кнопку-скрепку (она теперь живёт в поле ввода, а не отдельной
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
        attachProps: {
          loading: busy,
          onClick: (e: React.MouseEvent) => {
            e.stopPropagation();
            fileInputRef.current?.click();
          },
        } as React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean },
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

interface TopicHomeworkCardProps {
  lesson: LessonInfo;
  lessonId: number;
  canEdit: boolean;
  onTopicChange: (topic: string) => void;
  onHomeworkChange: (homework: string) => void;
  onAnswerRequiredChange: (value: boolean) => void;
  onAssignmentCreated: (id: number) => void;
  /** Вход на экран «Заданий» с фильтром по этому уроку. Оценки за ДЗ в
   *  журнале не ставятся — они живут в задании, поэтому карточка ведёт туда.
   *  Счётчик — сколько заданий к проверке (0 тоже показываем явно). */
  onCheckHomework?: () => void;
}

/**
 * Карточка «Тема · ДЗ» (вариант B, свёрнутая): превью одной строкой,
 * раскрытие по тапу. В развёрнутом виде — два поля ввода (canEdit) или текст.
 */
export const TopicHomeworkCard: React.FC<TopicHomeworkCardProps> = ({
  lesson,
  lessonId,
  canEdit,
  onTopicChange,
  onHomeworkChange,
  onAnswerRequiredChange,
  onAssignmentCreated,
  onCheckHomework,
}) => {
  const [expanded, setExpanded] = React.useState(false);
  // Скрепка в поле ввода ДЗ нужна ВСЕГДА, пока учитель может редактировать
  // урок: и до создания задания (скрепка создаст его), и после (допишет
  // файл в существующее). Раньше она пряталась при homework_assignment_id —
  // ровно то, на что ты указал.
  const [materialsRev, setMaterialsRev] = React.useState(0);
  const { attachProps, hiddenInput, error: hwError } = useLessonMaterials(
    lessonId, onAssignmentCreated, () => setMaterialsRev(v => v + 1),
  );
  const hwAttachProps = canEdit ? attachProps : null;
  const toReview = lesson.hw_to_review ?? 0;

  /* Проверка ДЗ: оценки за ДЗ в журнале не ставятся — они живут в задании,
     поэтому отсюда один вход на готовый экран «Заданий», отфильтрованный
     по этому уроку (предмет + класс). Показываем в обоих состояниях
     карточки — свёрнутом и раскрытом, учителю не нужно ничего раскрывать.
     Оформление как у всех кнопок миниаппа: ярко-синяя primary accent,
     по ширине контента, не во весь экран, и прижата к ПРАВОМУ краю —
     в одной строке с превью темы (шеврон раскрытия уходит перед ней).
     Счётчик — ВНУТРИ кнопки, справа от слова: поэтому содержимое
     обёрнуто в Flex. Без обёртки счётчик уезжает под текст —
     vkuiCounter__host это display:flex, то есть блочный элемент, и
     рядом с инлайновым текстом он роняет строку. Счётчик
     mode="contrast" — белым по синему, иначе не читается.
     Ноль показываем явно: «проверять нечего» — тоже ответ, без него
     непонятно, кнопка сломана или работать не над чем. Число приезжает
     в том же ответе /api/lesson/<id>/students (hw_to_review) и считает
     ЗАДАНИЯ, а не работы. */
  const checkButton = onCheckHomework ? (
    <Button
      size="l"
      mode="primary"
      appearance="accent"
      onClick={e => { e.stopPropagation(); onCheckHomework(); }}
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

  // Пустая тема — пунктирная рамка без заливки (вариант 3 мокапа
  // topic-card-variants.html), тень elevation3 — заметно плотнее карточек
  // учеников (elevation2), чтобы зона выделялась; заполненная — белая
  // карточка с той же elevation3 (независимо от заполненности).
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
        /* Свёрнуто: превью темы и ДЗ, шеврон раскрытия и кнопка «Проверить»
           в самом правом краю. Кнопка не растянута, поэтому текст превью
           ужимается эллипсом, а не выталкивает её за экран (minWidth: 0
           у колонки превью — иначе flex не даёт сжать текст). */
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
            <Caption level="1" weight="2" style={{ color: 'var(--vkui--color_text_secondary)' }}>
              ДОМАШНЕЕ ЗАДАНИЕ
            </Caption>
            {canEdit ? (
              /* Скрепка — ВНУТРИ поля, справа, как в мессенджерах (Telegram,
                 WhatsApp): слово «Материалы» не нужно, значок всё говорит.
                 В VKUI 8 у Input нет слота под иконку (slotProps только
                 прокидывает пропы), поэтому поле и кнопку кладём в один
                 контейнер: relative у контейнера, кнопка absolute поверх
                 поля, а у самого input paddingRight — иначе текст ДЗ уезжал
                 бы под скрепку. Размер кнопки совпадает с полем, иначе
                 она «провисает» по краю рамки.
                 onClick с stopPropagation — иначе тап по скрепке раскрыл бы
                 карточку. Файл не обязателен: скрепка создаст задание сама
                 (POST /lesson/<id>/materials), даже если текст ДЗ пуст. */
              <Box style={{ position: 'relative' }}>
                <Input
                  value={lesson.homework}
                  onChange={e => onHomeworkChange(e.target.value)}
                  placeholder="Например: §14, №412–418 или фото доски"
                  aria-label="Домашнее задание"
                  /* Отступ текста — именно у самого <input> (slotProps.input),
                     а не у компонента: style на Input уходит на хост, и
                     отступ там текст бы не сдвинул, текст лежал бы под
                     скрепкой. */
                  slotProps={hwAttachProps
                    ? { input: { style: { paddingRight: 40 } } }
                    : undefined}
                />
                {hwAttachProps && (
                  <Box
                    style={{
                      position: 'absolute', right: 0, top: 0, bottom: 0,
                      display: 'flex', alignItems: 'center',
                    }}
                  >
                    <Button
                      size="s"
                      mode="tertiary"
                      appearance="neutral"
                      aria-label="Прикрепить фото или файл"
                      onClick={e => e.stopPropagation()}
                      style={{
                        height: 'var(--vkui--size_field_height--regular)',
                        width: 40, minWidth: 40, padding: 0,
                        borderRadius: 'var(--vkui--size_border_radius--regular)',
                      }}
                      {...hwAttachProps}
                    >
                      <Icon28AttachOutline width={20} height={20} />
                    </Button>
                  </Box>
                )}
              </Box>
            ) : (
              <Text>{lesson.homework || '—'}</Text>
            )}
            {canEdit && lesson.homework && !lesson.homework_assignment_id && (
              <Caption level="1" style={{ color: 'var(--vkui--color_text_positive)' }}>
                При сохранении будет создано задание со сроком на следующий урок
              </Caption>
            )}
          </Flex>

          {canEdit && lesson.homework && (
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
              прикрепления через скрепку. */}
          {canEdit && lesson.homework_assignment_id && (
            <MaterialsEditor
              key={`${lesson.homework_assignment_id}:${materialsRev}`}
              assignmentId={lesson.homework_assignment_id}
              showAttachButton={false}
            />
          )}
          {canEdit && hwError && (
            <Caption level="1" style={{ color: 'var(--vkui--color_text_negative)' }}>
              {hwError}
            </Caption>
          )}
          {hiddenInput}

          {/* В раскрытом виде кнопка тоже у правого края — тем же боком,
              что и в свёрнутом, чтобы при раскрытии ничего не «прыгало». */}
          {checkButton && (
            <Flex justify="end">{checkButton}</Flex>
          )}

          <Button
            size="s"
            mode="tertiary"
            appearance="neutral"
            before={<Icon24ChevronUp />}
            onClick={() => setExpanded(false)}
          >
            Свернуть
          </Button>
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
