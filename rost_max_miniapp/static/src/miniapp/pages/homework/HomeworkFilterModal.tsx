/**
 * Шторка фильтров «Задания» учителя/админа (мокап
 * design/teacher-homework-mockup.html): ModalPage с рядами чипов
 * «Классы» и «Предметы», черновик выбора применяется по «Показать».
 * Чипы идут в горизонтальную обёртку (flex-wrap) — компактно по
 * высоте; выбранный чип = mode primary, снятый = secondary.
 *
 * Значения собираются из уже загруженного списка заданий (не из
 * справочников) — фильтр по определению не может дать пустую опцию.
 * Домены групп И между полями, ИЛИ внутри одного поля.
 *
 * ВАЖНО: AppRootPortal usePortal обязателен. .vkuiView__panel держит
 * isolation:isolate, а AppRoot у нас mode="full" — без явного usePortal
 * портал НЕ создаётся, z-index модалки (99) не выходит из
 * stacking-контекста View, и fixed таббар Epic (z=2, в DOM позже View)
 * перекрывает нижние кнопки шторки.
 */
import React from 'react';
import {
  ModalPage, ModalPageHeader, PanelHeaderButton, Group, Header, Chip,
  Button, ButtonGroup, Footnote, AppRootPortal,
} from '@vkontakte/vkui';
import { Icon24Dismiss } from '@vkontakte/icons';
import type { TeacherHomeworkItem } from '@/shared/lib/types';

export interface HomeworkFilters {
  batches: Set<string>;
  subjects: Set<string>;
}

interface Props {
  open: boolean;
  items: TeacherHomeworkItem[];
  /** Активный фильтр (то, что сейчас применено к ленте). */
  value: HomeworkFilters;
  onClose: () => void;
  onApply: (f: HomeworkFilters) => void;
}

/** Уникальные отсортированные значения поля по всем заданиям. */
const collect = (items: TeacherHomeworkItem[], key: 'batch' | 'subject'): string[] =>
  [...new Set(items.map(h => h[key]))].sort((a, b) =>
    a.localeCompare(b, 'ru', { numeric: true }));

export const HomeworkFilterModal: React.FC<Props> = ({
  open, items, value, onClose, onApply,
}) => {
  // Черновик: живёт пока шторка открыта, «Отмена»/крестик его отбрасывают.
  const [draftBatches, setDraftBatches] = React.useState<Set<string>>(new Set());
  const [draftSubjects, setDraftSubjects] = React.useState<Set<string>>(new Set());

  // При открытии черновик = применённый фильтр.
  React.useEffect(() => {
    if (open) {
      setDraftBatches(new Set(value.batches));
      setDraftSubjects(new Set(value.subjects));
    }
  }, [open, value]);

  const batchOptions = React.useMemo(() => collect(items, 'batch'), [items]);
  const subjectOptions = React.useMemo(() => collect(items, 'subject'), [items]);

  const toggle = (
    setter: React.Dispatch<React.SetStateAction<Set<string>>>,
    set: Set<string>, v: string,
  ) => {
    const next = new Set(set);
    if (next.has(v)) next.delete(v); else next.add(v);
    setter(next);
  };

  const draftEmpty = draftBatches.size === 0 && draftSubjects.size === 0;

  const reset = () => {
    setDraftBatches(new Set());
    setDraftSubjects(new Set());
  };

  const apply = () => onApply({ batches: draftBatches, subjects: draftSubjects });

  const renderSection = (
    header: string,
    options: string[],
    selected: Set<string>,
    setter: React.Dispatch<React.SetStateAction<Set<string>>>,
  ) => (
    <Group
      header={<Header size="s">{header}</Header>}
      mode="plain"
      separator="hide"
    >
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 8, padding: '0 16px 8px',
      }}>
        {options.map(opt => {
          const active = selected.has(opt);
          return (
            <Chip
              key={opt}
              removable={false}
              onClick={() => toggle(setter, selected, opt)}
              aria-pressed={active}
              style={active ? {
                background: 'var(--vkui--color_background_accent)',
                border: '1px solid var(--vkui--color_background_accent)',
              } : {
                background: 'var(--vkui--color_background_secondary)',
                border: '1px solid transparent',
              }}
            >
              <span style={{
                color: active
                  ? 'var(--vkui--color_text_contrast)'
                  : 'var(--vkui--color_text_secondary)',
                fontWeight: active ? 600 : 400,
              }}>
                {opt}
              </span>
            </Chip>
          );
        })}
      </div>
    </Group>
  );

  return (
    <AppRootPortal usePortal>
      <ModalPage
        id="teacher-homework-filters"
        open={open}
        onClose={onClose}
        dynamicContentHeight
        header={(
          <ModalPageHeader
            before={(
              <PanelHeaderButton onClick={onClose} aria-label="Закрыть">
                <Icon24Dismiss />
              </PanelHeaderButton>
            )}
            after={(
              <PanelHeaderButton
                onClick={reset}
                disabled={draftEmpty}
              >
                Сбросить
              </PanelHeaderButton>
            )}
          >
            Фильтры
          </ModalPageHeader>
        )}
      >
        {items.length === 0 ? (
          <Footnote style={{ padding: 16 }}>
            Пока нет заданий — фильтровать нечего.
          </Footnote>
        ) : (
          <>
            {renderSection('Классы', batchOptions, draftBatches, setDraftBatches)}
            {renderSection('Предметы', subjectOptions, draftSubjects, setDraftSubjects)}
            <div style={{ padding: '4px 16px 12px' }}>
              <ButtonGroup gap="s" stretched>
                <Button size="l" mode="primary" stretched onClick={apply}>
                  Ок
                </Button>
                <Button
                  size="l"
                  mode="secondary"
                  stretched
                  onClick={onClose}
                >
                  Отмена
                </Button>
              </ButtonGroup>
            </div>
          </>
        )}
      </ModalPage>
    </AppRootPortal>
  );
};
