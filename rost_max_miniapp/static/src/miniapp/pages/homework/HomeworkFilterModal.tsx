/**
 * Шторка фильтров «Задания» учителя/админа — тонкая обёртка над общим
 * ChipFilterModal (мокап design/teacher-homework-mockup.html). Секции
 * «Классы» и «Предметы» собираются из уже загруженного списка заданий
 * (не из справочников) — фильтр по определению не может дать пустую
 * опцию. Домены групп И между полями, ИЛИ внутри одного поля.
 */
import React from 'react';
import { ChipFilterModal } from '@/shared/components/ChipFilterModal';
import type { ChipFilterSection } from '@/shared/components/ChipFilterModal';
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
  const sections: ChipFilterSection[] = React.useMemo(() => [
    { key: 'batches', header: 'Классы',
      options: collect(items, 'batch').map(v => ({ value: v })) },
    { key: 'subjects', header: 'Предметы',
      options: collect(items, 'subject').map(v => ({ value: v })) },
  ], [items]);

  return (
    <ChipFilterModal
      open={open}
      id="teacher-homework-filters"
      emptyText="Пока нет заданий — фильтровать нечего."
      sections={sections}
      value={{ batches: value.batches, subjects: value.subjects }}
      onClose={onClose}
      onApply={f => onApply({
        batches: f.batches ?? new Set(),
        subjects: f.subjects ?? new Set(),
      })}
    />
  );
};
