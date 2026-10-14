/**
 * Общая шторка чип-фильтров (мокап design/grades-filters.html): ModalPage
 * с секциями чипов, «Сбросить» в шапке, футер «Отмена / Ок» (порядок
 * кнопок задаёт footerOrder — в «Заданиях» исторически Ок слева).
 * Выделена из HomeworkFilterModal («Задания» учителя): тот же паттерн
 * переиспользует «Мои пары» вкладки Оценки; секции задаёт вызывающий.
 *
 * Черновик выбора живёт, пока шторка открыта, «Отмена»/крестик его
 * отбрасывают; применяется по «Ок». Опции собирает ВЫЗЫВАЮЩИЙ из уже
 * загруженных данных — фильтр по определению не может дать пустую опцию.
 * Домены: И между секциями, ИЛИ внутри одной.
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

/** Применённый фильтр: ключ секции -> выбранные значения (пустой Set = «все»). */
export type ChipFilters = Record<string, Set<string>>;

export interface ChipFilterOption {
  value: string;
  /** Счётчик объектов с этим значением (мокап: цифра внутри чипа). */
  count?: number;
}

export interface ChipFilterSection {
  key: string;
  header: string;
  options: ChipFilterOption[];
}

interface Props {
  open: boolean;
  /** id ModalPage — держим уникальным на страницу. */
  id?: string;
  /** Текст, когда фильтровать нечего (список источников пуст). */
  emptyText?: string;
  sections: ChipFilterSection[];
  /** Активный фильтр (то, что сейчас применено к ленте). */
  value: ChipFilters;
  onClose: () => void;
  onApply: (f: ChipFilters) => void;
  /** Порядок кнопок футера. 'ok-first' — как в «Заданиях», 'cancel-first' — как в мокапе «Оценок». */
  footerOrder?: 'ok-first' | 'cancel-first';
  /** Черновик тапа отдаётся наверх: вызывающий пересчитывает секции
   *  (фасетный поиск — опции сужаются прямо в открытой шторке). */
  onDraftChange?: (d: ChipFilters) => void;
}

/** Строка чипов применённого фильтра над лентой + «Сбросить» справа
 *  (общая для «Заданий» и «Моих пар» — kind непрозрачен для вызывающего). */
export const FilterChipRow: React.FC<{
  chips: { kind: string; v: string }[];
  onRemove: (kind: string, v: string) => void;
  onReset: () => void;
}> = ({ chips, onRemove, onReset }) => {
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

export const ChipFilterModal: React.FC<Props> = ({
  open, id = 'chip-filters', emptyText, sections, value, onClose, onApply,
  footerOrder = 'ok-first', onDraftChange,
}) => {
  // Черновик: живёт пока шторка открыта, «Отмена»/крестик его отбрасывают.
  const [draft, setDraft] = React.useState<ChipFilters>({});

  // value/sections читаются ТОЛЬКО при открытии (через ref): после этого
  // черновик принадлежит шторке — иначе пересчёт секций вызывающим
  // (фасетное сужение) сбрасывал бы выбор пользователя на каждом тапе.
  const valueRef = React.useRef(value);
  const sectionsRef = React.useRef(sections);
  valueRef.current = value;
  sectionsRef.current = sections;

  React.useEffect(() => {
    if (open) {
      const next: ChipFilters = {};
      for (const s of sectionsRef.current) {
        next[s.key] = new Set(valueRef.current[s.key] ?? []);
      }
      setDraft(next);
    }
  }, [open]);

  const commit = (d: ChipFilters) => {
    setDraft(d);
    onDraftChange?.(d);
  };

  const toggle = (key: string, v: string) => {
    const next = new Set(draft[key] ?? []);
    if (next.has(v)) next.delete(v); else next.add(v);
    commit({ ...draft, [key]: next });
  };

  const draftEmpty = sections.every(s => (draft[s.key]?.size ?? 0) === 0);

  const reset = () => {
    const next: ChipFilters = {};
    for (const s of sections) next[s.key] = new Set();
    commit(next);
  };

  const apply = () => {
    // Секции без выбранных значений отдаём пустыми Set — вызывающий
    // хранит все ключи в одном состоянии.
    const out: ChipFilters = {};
    for (const s of sections) out[s.key] = new Set(draft[s.key] ?? []);
    onApply(out);
  };

  const renderSection = (s: ChipFilterSection) => (
    <Group
      key={s.key}
      header={<Header size="s">{s.header}</Header>}
      mode="plain"
      separator="hide"
    >
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 8, padding: '0 16px 8px',
      }}>
        {s.options.map(opt => {
          const active = (draft[s.key]?.has(opt.value)) ?? false;
          return (
            <Chip
              key={opt.value}
              removable={false}
              onClick={() => toggle(s.key, opt.value)}
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
                {opt.value}
                {opt.count != null && (
                  <span style={{
                    opacity: 0.65, fontWeight: 400, marginLeft: 5, fontSize: 12,
                  }}>
                    {opt.count}
                  </span>
                )}
              </span>
            </Chip>
          );
        })}
      </div>
    </Group>
  );

  const footer = (
    <div style={{ padding: '4px 16px 12px' }}>
      <ButtonGroup gap="s" stretched>
        {footerOrder === 'cancel-first' ? (
          <>
            <Button size="l" mode="secondary" stretched onClick={onClose}>
              Отмена
            </Button>
            <Button size="l" mode="primary" stretched onClick={apply}>
              Ок
            </Button>
          </>
        ) : (
          <>
            <Button size="l" mode="primary" stretched onClick={apply}>
              Ок
            </Button>
            <Button size="l" mode="secondary" stretched onClick={onClose}>
              Отмена
            </Button>
          </>
        )}
      </ButtonGroup>
    </div>
  );

  return (
    <AppRootPortal usePortal>
      <ModalPage
        id={id}
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
        {sections.every(s => s.options.length === 0) ? (
          <Footnote style={{ padding: 16 }}>
            {emptyText ?? 'Фильтровать нечего.'}
          </Footnote>
        ) : (
          <>
            {sections.map(renderSection)}
            {footer}
          </>
        )}
      </ModalPage>
    </AppRootPortal>
  );
};
