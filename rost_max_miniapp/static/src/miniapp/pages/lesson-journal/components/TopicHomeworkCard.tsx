// Прикрепление материалов ДЗ прямо из журнала урока. Кнопка видна ВСЕГДА,
// пока учитель может редактировать урок: текст ДЗ не обязателен — фото
// доски само создаёт задание (бэкенд: POST /lesson/<id>/materials).
// Когда задание уже есть — работаем с ним напрямую через MaterialsEditor.
// Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { Box, Flex, Text, Caption, Input, Button, Checkbox } from '@vkontakte/vkui';
import { Icon24ChevronDown, Icon24ChevronUp, Icon28AttachOutline } from '@vkontakte/icons';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { apiPost, fileToBase64 } from '@/shared/lib/api';
import type { LessonInfo } from '@/shared/lib/types';

interface LessonMaterialsProps {
  lessonId: number;
  onAssignmentCreated: (id: number) => void;
}

const LessonMaterials: React.FC<LessonMaterialsProps> = ({
  lessonId, onAssignmentCreated,
}) => {
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
      }
    } catch {
      setError('Не удалось прикрепить');
    }
    setBusy(false);
  };

  return (
    <div onClick={e => e.stopPropagation()}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        multiple
        style={{ display: 'none' }}
        onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
      />
      <Button
        size="s"
        mode="tertiary"
        loading={busy}
        before={<Icon28AttachOutline width={18} height={18} />}
        onClick={() => fileInputRef.current?.click()}
      >
        Прикрепить
      </Button>
      {error && (
        <Caption level="1" style={{ color: 'var(--vkui--color_text_negative)' }}>
          {error}
        </Caption>
      )}
    </div>
  );
};

interface TopicHomeworkCardProps {
  lesson: LessonInfo;
  lessonId: number;
  canEdit: boolean;
  onTopicChange: (topic: string) => void;
  onHomeworkChange: (homework: string) => void;
  onAnswerRequiredChange: (value: boolean) => void;
  onAssignmentCreated: (id: number) => void;
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
}) => {
  const [expanded, setExpanded] = React.useState(false);
  const hasContent = Boolean(lesson.topic || lesson.homework || lesson.homework_assignment_id);
  const previewTopic = lesson.topic || 'Тема не указана';
  const previewHw = lesson.homework
    ? `ДЗ: ${lesson.homework}`
    : (lesson.homework_assignment_id ? 'ДЗ: фото/материалы' : 'ДЗ не задано');

  return (
    <Box
      padding="m"
      onClick={() => setExpanded(v => !v)}
      style={{
        backgroundColor: 'var(--vkui--color_background_content)',
        borderRadius: 'var(--vkui--border_radius_l)',
        cursor: 'pointer',
      }}
    >
      {!expanded ? (
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
              <Input
                value={lesson.homework}
                onChange={e => onHomeworkChange(e.target.value)}
                placeholder="Например: §14, №412–418 или фото доски"
                aria-label="Домашнее задание"
              />
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

          {/* Материалы ДЗ: задание есть — редактируем его; нет — кнопка
              «Прикрепить» создаст задание сама (текст не обязателен). */}
          {canEdit && lesson.homework_assignment_id && (
            <MaterialsEditor assignmentId={lesson.homework_assignment_id} />
          )}
          {canEdit && !lesson.homework_assignment_id && (
            <LessonMaterials
              lessonId={lessonId}
              onAssignmentCreated={onAssignmentCreated}
            />
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
        <Caption level="1" style={{ color: 'var(--vkui--color_text_secondary)', marginTop: 4 }}>
          Нажмите, чтобы заполнить
        </Caption>
      )}
    </Box>
  );
};
