import React from 'react';
import { Text, Caption, IconButton } from '@vkontakte/vkui';
import { Icon28ChevronBack, Icon28FlashOutline, Icon28SettingsOutline } from '@vkontakte/icons';
import { shortBatchName } from '@/shared/components/LessonRow';

interface LessonHeaderProps {
  lesson: {
    subject?: string; batch?: string; timing?: string;
    /** Четверть урока (api_lesson_students). Нет значения — не показываем. */
    quarter?: number | null;
  } | null;
  onBack: () => void;
  onOpenBulkSheet?: () => void;
  onOpenColumnsSettings?: () => void;
}

/**
 * Хедер журнала: назад слева, предмет и контекст урока по центру, справа
 * молния (массовая простановка) и шестерёнка (колонки).
 *
 * Свой div вместо VKUI PanelHeader — намеренно. PanelHeader на части
 * вьюпортов рисуется фиксированным и оставляет в потоке спейсер высотой
 * шапки, а desktop-рамка (desktop-frame.css) ещё и отодвигает его на 40px.
 * В сумме между шапкой и карточкой «Тема · ДЗ» висела пустая полоса,
 * которой нет в макете. Здесь высота и отступы заданы явно, в ритме
 * TabHeader корневых табов: padding 12/16/6, заголовок 20, контекст 12.
 */
export const LessonHeader: React.FC<LessonHeaderProps> = ({
  lesson,
  onBack,
  onOpenBulkSheet,
  onOpenColumnsSettings,
}) => {
  const headerTitle = lesson ? (lesson.subject || 'Журнал оценок') : 'Журнал оценок';
  // «5 А · 12:20 - 13:00 · 1 четверть». Класс режем через shortBatchName:
  // в базе он с учебным годом («5 А  2026/2027»), а в расписании и чипах
  // фильтров — короткий, и расхождение бросалось в глаза.
  const contextLine = lesson
    ? [
        lesson.batch ? shortBatchName(lesson.batch) : '',
        lesson.timing,
        lesson.quarter != null ? `${lesson.quarter} четверть` : '',
      ].filter(Boolean).join(' · ')
    : '';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '12px 16px 6px',
    }}>
      <IconButton label="Назад" onClick={onBack} style={{ flexShrink: 0 }}>
        <Icon28ChevronBack />
      </IconButton>

      <div style={{ flexGrow: 1, minWidth: 0 }}>
        <Text weight="2" style={{
          fontSize: 20,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {headerTitle}
        </Text>
        {contextLine && (
          <Caption level="1" style={{
            display: 'block',
            color: 'var(--vkui--color_text_secondary)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {contextLine}
          </Caption>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
        {onOpenBulkSheet && (
          <IconButton
            label="Массово проставить оценки и посещаемость"
            onClick={onOpenBulkSheet}
          >
            <Icon28FlashOutline />
          </IconButton>
        )}
        {onOpenColumnsSettings && (
          <IconButton label="Настройки журнала" onClick={onOpenColumnsSettings}>
            <Icon28SettingsOutline />
          </IconButton>
        )}
      </div>
    </div>
  );
};
