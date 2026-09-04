import React from 'react';
import { Box, Flex, Text, Caption, Input, Button } from '@vkontakte/vkui';
import { Icon24ChevronDown, Icon24ChevronUp } from '@vkontakte/icons';
import type { LessonInfo } from '@/shared/lib/types';

interface TopicHomeworkCardProps {
  lesson: LessonInfo;
  canEdit: boolean;
  onTopicChange: (topic: string) => void;
  onHomeworkChange: (homework: string) => void;
}

/**
 * Карточка «Тема · ДЗ» (вариант B, свёрнутая): превью одной строкой,
 * раскрытие по тапу. В развёрнутом виде — два поля ввода (canEdit) или текст.
 */
export const TopicHomeworkCard: React.FC<TopicHomeworkCardProps> = ({
  lesson,
  canEdit,
  onTopicChange,
  onHomeworkChange,
}) => {
  const [expanded, setExpanded] = React.useState(false);
  const hasContent = Boolean(lesson.topic || lesson.homework);
  const previewTopic = lesson.topic || 'Тема не указана';
  const previewHw = lesson.homework ? `ДЗ: ${lesson.homework}` : 'ДЗ не задано';

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
                placeholder="Например: §14, №412–418"
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
