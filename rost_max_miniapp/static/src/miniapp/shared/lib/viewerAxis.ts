/**
 * Ось «Кого смотрим» (решение Миши 2026-10-14): выбор ребёнка и режима
 * «Мои уроки» — секция в шторке фильтров, а не свитч на главной.
 * Режима «Школа» больше нет (решение Миши 2026-10-14): «Мои уроки» —
 * единственный недетский вариант, по умолчанию.
 * Хук отдаёт секцию для ChipFilterModal, чип над лентой и apply.
 *
 * Оси НЕТ у тех, кому переключать нечего (единственный вариант):
 * ученик, родитель с одним ребёнком, учитель/админ без детей и без детей
 * вообще. У staff с детьми — «Мои уроки» + дети, у родителя 2+ — дети.
 */
import React from 'react';
import { useAppStore } from './store';
import type { ChipFilterSection } from '@/shared/components/ChipFilterModal';
import type { ChildInfo } from './types';

export interface ViewerAxis {
  /** Секция для шторки (single-select, options без счётчиков). */
  section: ChipFilterSection;
  /** Текущее значение: 'mine' | 'child:<id>'. */
  value: string;
  labelOf: (v: string) => string;
  /** Подпись чипа над лентой для текущего режима. */
  chipLabel: string;
  /** × у чипа: staff и не дефолт («Мои уроки»); у родителя чип-индикатор. */
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

  // Остаток schoolMode из старой сессии (sessionStorage) гасим: режима
  // «Школа» больше нет. Ребёнка НЕ сбрасываем — у родителя сброс давал
  // запросы без child_id (дефолт ставит loadUserInfo).
  React.useEffect(() => {
    if (schoolMode) setSchoolMode(false);
  }, [schoolMode, setSchoolMode]);

  if (!userInfo) return null;
  const kids: ChildInfo[] = userInfo.children ?? [];
  const isStaff = Boolean(userInfo.is_teacher || userInfo.is_admin);

  // Опции по АККАУНТУ: staff — «Мои уроки» + дети, родитель — дети.
  const values = [
    ...(isStaff ? ['mine'] : []),
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
    const k = kids.find(x => `child:${x.id}` === v);
    return k ? kidLabel(k) : v;
  };
  const value = selectedChildId != null
    ? `child:${selectedChildId}`
    : 'mine';

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
    nonDefault: value !== 'mine',
    apply: (v: string) => {
      if (v === 'mine') {
        setChildId(null);
        setSchoolMode(false);
      } else if (v.startsWith('child:')) {
        setChildId(Number(v.slice(6)));
        setSchoolMode(false);
      }
    },
  };
}

/** Разбор значения секции «Кого смотрим» из шторки. Пустой Set после
 *  «Сбросить» в шторке: staff → дефолт «Мои уроки», родитель → без
 *  изменений (остаться без ребёнка он не может). */
export function viewerFromDraft(draft: Set<string> | undefined, axis: ViewerAxis): string {
  const v = [...(draft ?? [])][0];
  if (v != null) return v;
  return axis.chipRemovable ? 'mine' : axis.value;
}
