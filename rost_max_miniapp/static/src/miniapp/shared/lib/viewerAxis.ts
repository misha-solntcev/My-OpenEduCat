/**
 * Ось «Кого смотрим» (решение Миши 2026-10-14/15): фильтр-чип в шторке
 * фильтров, а не свитч на главной. Чип СУЖАЕТ информацию, снятый фильтр
 * = вся школа — у ЛЮБОГО staff (как в ПК: read учителя не сужен,
 * «Мои уроки» — снимаемый дефолтный фильтр act_window).
 * Значения: 'mine' («Мои уроки»), 'child:<id>', 'school' = фильтр снят
 * (чипа нет, обзор всей школы). Дефолт staff — «Мои уроки» с ×.
 * Родитель пустым остаться не может: чип ребёнка, дефолт первый.
 * «Школа» как ОТДЕЛЬНЫЙ вариант в шторке НЕТ (решение Миши 2026-10-15):
 * нет чипа = школа. Заголовок секции не рисуется.
 * Хук отдаёт секцию для ChipFilterModal, чип над лентой и apply.
 */
import React from 'react';
import { useAppStore } from './store';
import type { ChipFilterSection } from '@/shared/components/ChipFilterModal';
import type { ChildInfo } from './types';

export interface ViewerAxis {
  /** Секция для шторки (single-select; у staff с обзором — allowEmpty). */
  section: ChipFilterSection;
  /** Текущее значение: 'mine' | 'school' (фильтр снят) | 'child:<id>'. */
  value: string;
  labelOf: (v: string) => string;
  /** Подпись чипа над лентой ('school' — пусто, чип не рисуется). */
  chipLabel: string;
  /** × у чипа — только у staff с правом школьного обзора. */
  chipRemovable: boolean;
  /** Не дефолт — для подсветки кнопки фильтра. */
  nonDefault: boolean;
  apply: (v: string) => void;
}

export function useViewerAxis(): ViewerAxis | null {
  const userInfo = useAppStore(s => s.userInfo);
  const selectedChildId = useAppStore(s => s.selectedChildId);
  const schoolMode = useAppStore(s => s.schoolMode);
  const setChildId = useAppStore(s => s.setChildId);
  const setSchoolMode = useAppStore(s => s.setSchoolMode);

  if (!userInfo) return null;
  const kids: ChildInfo[] = userInfo.children ?? [];
  const isStaff = Boolean(userInfo.is_teacher || userInfo.is_admin);
  // Фильтр можно снять (обзор всей школы) у ЛЮБОГО staff — как в ПК:
  // учитель читает весь тайминг школы, «Мои уроки» — снимаемый дефолт.
  const canSchool = isStaff;

  // Ось есть у тех, у кого фильтр вообще есть: staff всегда («Мои уроки»
  // снимаем даже без детей), родитель — при 2+ детях. Ученику и
  // родителю-1 переключать нечего.
  const values = [
    ...(isStaff ? ['mine'] : []),
    ...kids.map(k => `child:${k.id}`),
  ];
  if (values.length < 2 && !canSchool) return null;

  // Подпись ребёнка: Фамилия Имя (решение Миши 2026-10-14) — дети одной
  // семьи различимы: «Макарова Василиса», «Макаров Михаил».
  const kidLabel = (k: ChildInfo): string =>
    `${k.name.split(' ').slice(0, 2).join(' ')} · ${k.batch}`;
  const labelOf = (v: string): string => {
    if (v === 'mine') return 'Мои уроки';
    const k = kids.find(x => `child:${x.id}` === v);
    return k ? kidLabel(k) : '';
  };
  const value = selectedChildId != null
    ? `child:${selectedChildId}`
    : (schoolMode ? 'school' : 'mine');

  // Остаток schoolMode у того, кому обзор школы не положен, гасим:
  // учитель в school-режиме бэк всё равно срежет до своих уроков.
  React.useEffect(() => {
    if (schoolMode && !canSchool) setSchoolMode(false);
  }, [schoolMode, canSchool, setSchoolMode]);

  return {
    section: {
      key: 'viewer',
      single: true,
      allowEmpty: canSchool,
      options: values.map(v => ({ value: v, label: labelOf(v) })),
    },
    value,
    labelOf,
    chipLabel: labelOf(value),
    chipRemovable: canSchool && value !== 'school',
    nonDefault: canSchool ? value !== 'school' : value.startsWith('child:'),
    apply: (v: string) => {
      if (v === 'school') {
        // Фильтр снят — обзор всей школы.
        setChildId(null);
        setSchoolMode(true);
      } else {
        setChildId(v === 'mine' ? null : Number(v.slice(6)));
        setSchoolMode(false);
      }
    },
  };
}

/** Чип «Кого смотрим» для FilterChipRow: [] — не рисовать (фильтр снят). */
export function viewerChips(axis: ViewerAxis):
    { kind: string; v: string; removable?: boolean }[] {
  return axis.chipLabel
    ? [{ kind: 'viewer', v: axis.chipLabel, removable: axis.chipRemovable }]
    : [];
}

/** Разбор значения секции «Кого смотрим» из шторки. Пустой Set («Сбросить»
 *  или тап по выбранному): у staff с правом обзора — фильтр снят (школа),
 *  иначе — без изменений (учителю/родителю пусто оставаться нельзя). */
export function viewerFromDraft(draft: Set<string> | undefined, axis: ViewerAxis): string {
  const v = [...(draft ?? [])][0];
  if (v != null) return v;
  return axis.chipRemovable ? 'school' : axis.value;
}
