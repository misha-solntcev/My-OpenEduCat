/**
 * Карточка задания учителя/админа и заголовки разделов — точная
 * сборка мокапа design/teacher-homework-mockup.html.
 *
 * Геометрия из мокапа (не выдумывать!):
 *   .inner    — 12px от краёв экрана (даёт родительский Box)
 *   .card     — padding 12, margin 6 0, radius 12, тень
 *   .subj-ic  — 38x38, radius 10, иконка 20x20 (цветной квадрат)
 *   .subj-name— 16px/600;  .subj-meta — 12px серый
 *   .pill     — 11px/600, padding 4 8, radius 8
 *   .task     — 15px/600, margin-top 6
 *   .desc     — 13px/1.45 серый, margin-top 2
 *   .cta      — синяя, 100%x40, radius 8, 14px/600, margin-top 10
 *   .gtitle   — 20px/600 + счётчик 16px/600, margin 26 0 10, padding 0 4
 *
 * Общее с ученическими карточками (палитра Odoo, контраст иконки)
 * продублировано локально: HomeworkCardList типизирован HomeworkItem.
 */
import React from 'react';
import { Caption, Text } from '@vkontakte/vkui';
import { SubjectIcon } from './SubjectIcon';
import type { TeacherHomeworkItem } from '@/shared/lib/types';

/* --- Палитра предметов (та же формула, что в HomeworkCardList) --- */

const ODOO_COLORS: { bg: string; color: string }[] = [
  { bg: '#cccccc', color: '#a2a2a2' }, { bg: '#f68c8c', color: '#ee2d2d' }, { bg: '#ecbc8f', color: '#dc8534' }, { bg: '#f2da83', color: '#e8bb1d' }, { bg: '#a3c4ec', color: '#5794dd' }, { bg: '#caa9c1', color: '#9f628f' }, { bg: '#ebbeaa', color: '#db8865' }, { bg: '#96d0cc', color: '#41a9a2' },
  { bg: '#8d9cee', color: '#304be0' }, { bg: '#f68dbf', color: '#ee2f8a' }, { bg: '#a8deaf', color: '#61c36e' }, { bg: '#c6b1f1', color: '#9872e6' }, { bg: '#d09cae', color: '#aa4b6b' }, { bg: '#8ddeba', color: '#30c381' }, { bg: '#c6b393', color: '#97743a' }, { bg: '#fbe484', color: '#f7cd1f' },
  { bg: '#97bcf9', color: '#4285f4' }, { bg: '#c187d0', color: '#8e24aa' }, { bg: '#e87ea7', color: '#d6145f' }, { bg: '#7f9598', color: '#173e43' }, { bg: '#8fc19f', color: '#348f50' }, { bg: '#d09392', color: '#aa3a38' }, { bg: '#b5a29a', color: '#795548' }, { bg: '#a6748e', color: '#5e0231' },
  { bg: '#aef1bc', color: '#6be585' }, { bg: '#c7c7ab', color: '#999966' }, { bg: '#f3e7a9', color: '#e9d362' }, { bg: '#d6acac', color: '#b56969' }, { bg: '#dbdee0', color: '#bdc3c7' }, { bg: '#aac2b2', color: '#649173' }, { bg: '#f373ff', color: '#ea00ff' }, { bg: '#ff7388', color: '#ff0026' },
  { bg: '#bfe373', color: '#8bcc00' }, { bg: '#73dcd3', color: '#00bfaf' }, { bg: '#73adff', color: '#006aff' }, { bg: '#d373dc', color: '#af00bf' }, { bg: '#dc7383', color: '#bf001d' }, { bg: '#dca973', color: '#bf6300' }, { bg: '#c0ff73', color: '#8cff00' }, { bg: '#73f8ff', color: '#00f2ff' },
  { bg: '#739bd5', color: '#004ab3' }, { bg: '#ff73e5', color: '#ff00d0' }, { bg: '#ffce73', color: '#ffa600' }, { bg: '#93e373', color: '#3acc00' }, { bg: '#73d7dc', color: '#00b6bf' }, { bg: '#739aff', color: '#0048ff' }, { bg: '#dcb773', color: '#bf7c00' }, { bg: '#75ff73', color: '#04ff00' },
  { bg: '#73e5ff', color: '#00d0ff' }, { bg: '#7390dc', color: '#0036bf' }, { bg: '#ff73c0', color: '#ff008c' }, { bg: '#73dc9b', color: '#00bf49' }, { bg: '#73c3d5', color: '#0092b3' }, { bg: '#7375ff', color: '#0004ff' }, { bg: '#d573a9', color: '#b20062' }, { bg: '#aac2b2', color: '#649173' },
];

/** Затемнение базового цвета до контраста 3:1 с пастельным фоном. */
const contrastingIconColor = (base: string, bg: string): string => {
  const rgb = (hex: string) => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  const luminance = (channels: number[]) => {
    const [r, g, b] = channels.map(channel => {
      const s = channel / 255;
      return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const channels = rgb(base);
  const background = luminance(rgb(bg));
  for (let step = 0; step <= 100; step++) {
    const darkened = channels.map(channel => Math.round(channel * (1 - step / 100)));
    const foreground = luminance(darkened);
    const contrast = (Math.max(background, foreground) + 0.05)
      / (Math.min(background, foreground) + 0.05);
    if (contrast >= 3) return `#${darkened.map(channel => channel.toString(16).padStart(2, '0')).join('')}`;
  }
  return '#000000';
};

// Палитра постоянна: считаем контраст один раз, не при рендере карточки.
const SUBJECT_COLORS = ODOO_COLORS.map(({ bg, color }) => ({
  bg, color: contrastingIconColor(color, bg),
}));

/** Цвет предмета (Integer op.subject.color) -> пастель + контрастная иконка.
 *  index = ((c-1)%55)+1 (см. HomeworkCardList: Алгебра color=4 -> #a3c4ec). */
const subjectColor = (color: number): { bg: string; color: string } => {
  if (!color) return {
    bg: 'var(--vkui--color_background_secondary)',
    color: 'var(--vkui--color_text_secondary)',
  };
  return SUBJECT_COLORS[((color - 1) % 55) + 1];
};

/* --- Заголовок раздела (.gtitle) --- */

/** Цвета секций из мокапа: янтарный / синий / зелёный. */
export const SECTION_TONES = {
  review: '#a86600',
  issued: '#2d81e0',
  checked: '#2e8b5e',
} as const;

export type SectionKey = keyof typeof SECTION_TONES;

/** .gtitle: flex, gap 8, padding 0 4, margin 26 0 10; h2 20px/600,
 *  счётчик 16px/600. Цвет — цвет секции. */
export const SectionTitle: React.FC<{
  tone: SectionKey;
  title: string;
  count: number;
  /** Первый раздел сразу под шапкой/фильтрами — без больших 26px сверху. */
  first?: boolean;
}> = ({ tone, title, count, first }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '0 4px', margin: first ? '8px 0 10px' : '26px 0 10px',
    color: SECTION_TONES[tone],
  }}>
    <Text weight="2" style={{ fontSize: 20, lineHeight: '24px', color: 'inherit' }}>
      {title}
    </Text>
    <span style={{ fontSize: 16, fontWeight: 600 }}>{count}</span>
  </div>
);

/* --- Плашки (.pill) --- */

const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн',
  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

export const fmtDueTeacher = (due: string): string => {
  if (!due) return '';
  const d = new Date(due);
  if (isNaN(d.getTime())) return due;
  return `до ${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`;
};

/** .pill: flex, gap 4, 11px/600, padding 4 8, radius 8. Цвет текста
 *  из мокапа (синий на тинте / янтарный / серый) — мокап светлый,
 *  в тёмной теме серый берём токеном. */
const pillStyle = (background: string, color: string): React.CSSProperties => ({
  display: 'flex', alignItems: 'center', gap: 4,
  fontSize: 11, fontWeight: 600, padding: '4px 8px', borderRadius: 8,
  whiteSpace: 'nowrap', flexShrink: 0,
  background, color,
});

const PILL_BLUE_BG = '#e8f0fe';
const PILL_AMBER_BG = '#fdf3e0';
const PILL_BLUE_TEXT = '#2d81e0';
const PILL_AMBER_TEXT = '#a86600';

/** Правая плашка по состоянию (мокап): «N новых» синяя, «Просрочено,
 * N не сдали» янтарная, «Сдали N из M» серые. Второе значение —
 * занята ли плашка чем-то кроме «Сдали»: тогда «Сдали» уходит в мету
 * (в мокапе встречается ровно один раз, не дублируется). */
export const RightPill: React.FC<{ h: TeacherHomeworkItem }> = ({ h }) => {
  const gray = () => pillStyle(
    'var(--vkui--color_background_secondary)',
    'var(--vkui--color_text_secondary)');
  if (h.state === 'finish') {
    return <span style={gray()}>Завершено</span>;
  }
  if (h.to_review > 0) {
    return (
      <span style={pillStyle(PILL_BLUE_BG, PILL_BLUE_TEXT)}>
        {`${h.to_review} новых`}
      </span>
    );
  }
  if (h.overdue && h.submitted < h.total) {
    return (
      <span style={pillStyle(PILL_AMBER_BG, PILL_AMBER_TEXT)}>
        {`Просрочено, ${h.total - h.submitted} не сдали`}
      </span>
    );
  }
  return <span style={gray()}>{`Сдали ${h.submitted} из ${h.total}`}</span>;
};

/** Плашка занята («N новых»/«Просрочено»/«Завершено»)? Тогда «Сдали»
 *  живёт в мете, а не в плашке. */
const pillBusy = (h: TeacherHomeworkItem): boolean =>
  h.state === 'finish' || h.to_review > 0 || (h.overdue && h.submitted < h.total);

/* --- Карточка задания (.card) --- */

interface TeacherHwCardProps {
  h: TeacherHomeworkItem;
  showFaculty: boolean;
  onOpen: (id: number) => void;
}

/** Карточка как в мокапе: .card padding 12, radius 12, margin 6 0;
 *  шапка .row1 (квадрат + название/мета + плашка), .task 15px/600,
 *  .desc 13px серый. Клик — экран задания. */
export const TeacherHwCard: React.FC<TeacherHwCardProps> = ({ h, showFaculty, onOpen }) => {
  const c = subjectColor(h.subject_color || 0);

  // .subj-meta: «Срок: до 20 сен · Сдали 9 из 24»; у админа первым
  // преподаватель. «Сдали» попадает сюда ТОЛЬКО когда плашка справа
  // занята («N новых»/«Просрочено»/«Завершено»), иначе оно в плашке —
  // в мокапе значение встречается один раз.
  const meta = [
    showFaculty && h.faculty,
    h.due ? `Срок: ${fmtDueTeacher(h.due)}` : '',
    pillBusy(h) ? `Сдали ${h.submitted} из ${h.total}` : '',
  ].filter(Boolean).join(' · ');

  // Текст задания = .task; пояснение (описание из поля задания, если
  // отличается) — .desc. В модели одно поле task, desc нет.
  return (
    <div
      onClick={() => onOpen(h.id)}
      style={{
        background: 'var(--vkui--color_background_content)',
        borderRadius: 12,
        margin: '6px 0',
        padding: 12,
        cursor: 'pointer',
        boxShadow: 'var(--vkui--elevation1)',
      }}
    >
      {/* .row1 */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
          {/* .subj-ic 38x38 r10 + svg 20x20 */}
          <span style={{
            width: 38, height: 38, borderRadius: 10, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: c.bg, color: c.color,
          }}>
            <SubjectIcon subject={h.subject} />
          </span>
          {/* .subj-txt */}
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
            <Text weight="2" style={{
              fontSize: 16, lineHeight: '20px', display: 'block',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {h.subject}{h.batch ? ` · ${h.batch}` : ''}
            </Text>
            <Caption style={{
              fontSize: 12, color: 'var(--vkui--color_text_secondary)',
              display: 'block', marginTop: 1,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {meta}
            </Caption>
          </div>
        </div>
        <RightPill h={h} />
      </div>
      {/* .task */}
      <div style={{
        fontSize: 15, fontWeight: 600, lineHeight: '20px',
        marginTop: 6, overflowWrap: 'break-word',
        color: 'var(--vkui--color_text_primary)',
      }}>
        {h.task}
      </div>
    </div>
  );
};
