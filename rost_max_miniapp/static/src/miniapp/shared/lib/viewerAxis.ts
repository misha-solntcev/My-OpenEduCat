/**
 * Ось «Кого смотрим» (решение Миши 2026-10-14/15): выбор ребёнка, режима
 * «Мои уроки» и «Школа» — секция в шторке фильтров, а не свитч на главной.
 * «Школа» — только админам и завучам (is_deputy): обзор всей школы
 * (Расписание; на главной — админский обзор). Учитель — только
 * «Мои уроки» и дети. Родитель — только дети (дефолт первый).
 * Хук отдаёт секцию для ChipFilterModal, чип над лентой и apply.
 *
 * Оси НЕТ у тех, кому переключать нечего (единственный вариант):
 * ученик, родитель с одним ребёнком, учитель/админ без детей и без детей
 * вообще. У staff с детьми — «Мои уроки» (+ «Школа») и дети, у родителя
 * 2+ — дети.
 */
import React from 'react';
import { useAppStore } from './store';
import type { ChipFilterSection } from '@/shared/components/ChipFilterModal';
import type { ChildInfo } from './types';

export interface ViewerAxis {
  /** Секция для шторки (single-select, options без счётчиков). */
  section: ChipFilterSection;
  /** Текущее значение: 'mine' | 'school' | 'child:<id>'. */
  value: string;
  labelOf: (v: string) => string;
  /** Подпись чипа над лентой для текущего режима. */
  chipLabel: string;
  /** × у чипа: staff и не дефолт («Мои уроки»); у родителя чип-индикатор. */
  chipRemovable: boolean;
  /** Показывать ли чип над лентой: у staff только не-дефолт (решение
   *  Миши 2026-10-15 — «Мои уроки» без крестика читался как залипший
   *  фильтр); у родителя чип-индикатор ребёнка всегда. */
  showChip: boolean;
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
  // «Школа» — обзор всей школы: админ или завуч (гасить остаток
  // schoolMode не нужно — режим снова валиден).
  const canSchool = Boolean(userInfo.is_admin || userInfo.is_deputy);

  // Опции по АККАУНТУ: staff — «Мои уроки» (+ «Школа») и дети,
  // родитель — дети (дефолт первый ставит loadUserInfo).
  const values = [
    ...(isStaff ? ['mine'] : []),
    ...(canSchool ? ['school'] : []),
    ...kids.map(k => `child:${k.id}`),
  ];
  // Меньше двух — переключать нечего: ученик, родитель-1, staff без детей.
  if (values.length < 2) return null;

  // Подпись ребёнка: Фамилия Имя (решение Миши 2026-10-14) — дети одной
  // семьи различимы: «Макарова Василиса», «Макаров Михаил».
  const kidLabel = (k: ChildInfo): string =>
    `${k.name.split(' ').slice(0, 2).join(' ')} · ${k.batch}`;
  const labelOf = (v: string): string => {
    if (v === 'mine') return 'Мои уроки';
    if (v === 'school') return 'Школа';
    const k = kids.find(x => `child:${x.id}` === v);
    return k ? kidLabel(k) : v;
  };
  const value = selectedChildId != null
    ? `child:${selectedChildId}`
    : (schoolMode && canSchool ? 'school' : 'mine');

  return {
    section: {
      key: 'viewer',
      header: 'Кого смотрим',
      single: true,
      options: values.map(v => ({ value: v, label: labelOf(v) })),
    },
    value,
    labelOf,
    chipLabel: labelOf(value),
    chipRemovable: isStaff && value !== 'mine',
    showChip: !isStaff || value !== 'mine',
    nonDefault: value !== 'mine',
    apply: (v: string) => {
      if (v === 'mine') {
        setChildId(null);
        setSchoolMode(false);
      } else if (v === 'school') {
        setChildId(null);
        setSchoolMode(true);
      } else if (v.startsWith('child:')) {
        setChildId(Number(v.slice(6)));
        setSchoolMode(false);
      }
    },
  };
}

/** Чип «Кого смотрим» для FilterChipRow: [] — не рисовать (дефолт staff). */
export function viewerChips(axis: ViewerAxis):
    { kind: string; v: string; removable?: boolean }[] {
  return axis.showChip
    ? [{ kind: 'viewer', v: axis.chipLabel, removable: axis.chipRemovable }]
    : [];
}

/** Разбор значения секции «Кого смотрим» из шторки. Пустой Set после
 *  «Сбросить» в шторке: staff → дефолт «Мои уроки», родитель → без
 *  изменений (остаться без ребёнка он не может). */
export function viewerFromDraft(draft: Set<string> | undefined, axis: ViewerAxis): string {
  const v = [...(draft ?? [])][0];
  if (v != null) return v;
  return axis.chipRemovable ? 'mine' : axis.value;
}
