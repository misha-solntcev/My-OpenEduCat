import React from 'react';
import { Caption, Text, Tappable, useColorScheme } from '@vkontakte/vkui';
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

export const SECTION_TONES = {
  review: '#216ebd',
  issued: 'var(--vkui--color_text_secondary)',
  checked: '#2e7d54',
} as const;

const statusColors = (dark: boolean) => ({
  review: { color: dark ? '#8fc3ff' : '#216ebd', background: dark ? '#20364f' : '#eaf3fe' },
  issued: { color: dark ? '#a8b4c2' : '#627086', background: dark ? '#323a45' : '#edf0f3' },
  checked: { color: dark ? '#83d3a7' : '#2e7d54', background: dark ? '#203c30' : '#e0f1e8' },
  red: { color: dark ? '#ff9d9d' : '#b4232c', background: dark ? '#432326' : '#fdeaea' },
});

export type SectionKey = keyof typeof SECTION_TONES;

export const SectionTitle: React.FC<{
  tone: SectionKey;
  title: string;
  count: number;
  first?: boolean;
}> = ({ tone, title, count, first }) => {
  const colors = statusColors(useColorScheme() === 'dark')[tone];
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      margin: first ? '4px 3px 10px' : '22px 3px 10px',
      color: tone === 'issued' ? SECTION_TONES.issued : colors.color,
    }}>
      <Text Component="h2" weight="2" style={{ fontSize: 16, fontWeight: 600, lineHeight: '22px', color: 'inherit', margin: 0 }}>
        {title}
      </Text>
      <span style={{
        fontSize: 12, fontWeight: 600, minWidth: 24, textAlign: 'center',
        padding: '3px 6px', borderRadius: 7, ...colors,
      }}>{count}</span>
    </div>
  );
};

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

export const RightPill: React.FC<{ h: TeacherHomeworkItem }> = ({ h }) => {
  const gray = () => pillStyle(
    'var(--vkui--color_background_secondary)',
    'var(--vkui--color_text_secondary)');
  if (h.state === 'finish') return <span style={gray()}>Завершено</span>;
  if (h.to_review > 0) {
    return <span style={pillStyle(PILL_BLUE_BG, PILL_BLUE_TEXT)}>{`${h.to_review} новых`}</span>;
  }
  if (h.overdue && h.submitted < h.total) {
    return <span style={pillStyle(PILL_AMBER_BG, PILL_AMBER_TEXT)}>{`Просрочено, ${h.total - h.submitted} не сдали`}</span>;
  }
  return <span style={gray()}>{`Сдали ${h.submitted} из ${h.total}`}</span>;
};


const CardFoot: React.FC<{ h: TeacherHomeworkItem }> = ({ h }) => {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: 8, flexWrap: 'wrap', marginTop: 12, paddingTop: 10,
      borderTop: '1px solid var(--vkui--color_separator_primary)',
      fontSize: 13, lineHeight: '18px', color: 'var(--vkui--color_text_secondary)',
    }}>
      <span>Сдали <strong style={{ color: 'var(--vkui--color_text_primary)' }}>{h.submitted}</strong> из {h.total}</span>
      {h.state === 'finish' && <span>Приём закрыт</span>}
    </div>
  );
};

/* --- Карточка задания (.card) --- */

interface TeacherHwCardProps {
  h: TeacherHomeworkItem;
  showFaculty: boolean;
  onOpen: (id: number) => void;
}

export const TeacherHwCard: React.FC<TeacherHwCardProps> = ({ h, showFaculty, onOpen }) => {
  const c = subjectColor(h.subject_color || 0);
  const colors = statusColors(useColorScheme() === 'dark');
  const overdue = h.state !== 'finish' && h.overdue;
  const due = fmtDueTeacher(h.due); // «до 24 сен»

  return (
    <Tappable
      Component="div"
      onClick={() => onOpen(h.id)}
      style={{
        background: 'var(--vkui--color_background_content)',
        border: '1px solid var(--vkui--color_separator_primary)',
        borderRadius: 16,
        margin: '0 0 9px',
        padding: 14,
        textAlign: 'left',
      }}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: '1 0 auto', width: 'max-content', maxWidth: '100%', minWidth: 0 }}>
          <span style={{
            width: 38, height: 38, borderRadius: 10, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: c.bg, color: c.color,
          }}>
            <SubjectIcon subject={h.subject} />
          </span>
          <div style={{ minWidth: 0, flex: 1 }}>
            <Text weight="2" style={{
              fontSize: 16, fontWeight: 600, lineHeight: '22px',
              whiteSpace: 'normal', overflowWrap: 'anywhere',
              color: 'var(--vkui--color_text_primary)',
            }}>
              {h.subject}{h.batch ? ` · ${h.batch}` : ''}
            </Text>
            {showFaculty && h.faculty && (
              <Caption style={{ fontSize: 13, lineHeight: '18px', color: 'var(--vkui--color_text_secondary)', overflowWrap: 'anywhere' }}>
                {h.faculty}
              </Caption>
            )}
            {h.topic && (
              <Text style={{ fontSize: 15, lineHeight: '20px', marginTop: 2, color: 'var(--vkui--color_text_primary)', overflowWrap: 'anywhere', display: 'block' }}>
                {h.topic}
              </Text>
            )}
          </div>
        </div>
        {/* Срок — цветной бейдж справа сверху (как у карточки ученика):
            красный тинт при просрочке, синий тинт в остальных случаях. */}
        {due && (
          <span style={{
            display: 'inline-flex', alignItems: 'center',
            fontSize: 12, fontWeight: 600, lineHeight: '18px',
            padding: '4px 10px', borderRadius: 999, whiteSpace: 'nowrap',
            flexShrink: 0,
            background: overdue ? colors.red.background : colors.review.background,
            color: overdue ? colors.red.color : colors.review.color,
          }}>
            {due}
          </span>
        )}
      </div>
      <div style={{
        fontSize: 15, fontWeight: 400, lineHeight: 1.5,
        marginTop: 11, overflowWrap: 'anywhere', whiteSpace: 'pre-wrap',
        color: 'var(--vkui--color_text_primary)',
      }}>
        {h.task}
      </div>
      {h.issued_at && (() => {
        const d = new Date(h.issued_at);
        return isNaN(d.getTime()) ? null : (
          <Caption style={{
            display: 'block', marginTop: 6,
            color: 'var(--vkui--color_text_secondary)',
          }}>
            {`Выдано ${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`}
          </Caption>
        );
      })()}
      <CardFoot h={h} />
    </Tappable>
  );
};
