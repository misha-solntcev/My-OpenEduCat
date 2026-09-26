import React from 'react';
import { Caption, Text, Tappable, useColorScheme } from '@vkontakte/vkui';
import { SubjectAvatar } from './SubjectIcon';
import type { TeacherHomeworkItem } from '@/shared/lib/types';

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
          <SubjectAvatar subject={h.subject} color={h.subject_color} />
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
