/**
 * Карточки экранов «Оценки» учителя (мокап
 * design/teacher-grades-mockup.html). Три уровня:
 *   PairCard      — пара «класс + предмет» со сводкой и последними оценками
 *   StudentRow    — ученик пары: средний, посещаемость, уроки, оценки
 *   SubjectCard   — предмет ученика; mine=true кликабельна, чужие приглушены
 *
 * Общие компоненты: SubjectAvatar (иконка и палитра предмета) и
 * GradeChip (чип оценки) — оба из JournalButton/SubjectIcon, свои копии
 * цветов и размеров чипов здесь запрещены.
 * Никакого своего CSS — только токены VKUI.
 */
import React from 'react';
import { Tappable, Text, Caption } from '@vkontakte/vkui';
import { SubjectAvatar } from './SubjectIcon';
import { GradeChip } from './JournalButton';
import type { TeacherPair, PairStudent, StudentSubjectCard } from '@/shared/lib/types';

export const fmtAvg = (v: number | null | undefined): string =>
  (v && v > 0 ? v.toFixed(2).replace('.', ',') : '—');

/** Чипы последних оценок из карточки предмета. */
export const GradeChips: React.FC<{
  grades: { grade: number; date: string }[];
  withDate?: boolean;
}> = ({ grades, withDate }) => {
  if (grades.length === 0) {
    return <span className="empty">—</span>;
  }
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
      {grades.slice(0, 6).map((g, i) => (
        <GradeChip key={`${g.grade}-${g.date}-${i}`} grade={g.grade}
          title={withDate ? g.date : undefined} />
      ))}
    </div>
  );
};

const StatBlock: React.FC<{ value: string; label: string }> = ({ value, label }) => (
  <div style={{ textAlign: 'center', minWidth: 40 }}>
    <b style={{ display: 'block', fontSize: 15, lineHeight: 1.1 }}>{value}</b>
    <i style={{
      fontStyle: 'normal', fontSize: 10,
      color: 'var(--vkui--color_text_secondary)',
    }}>
      {label}
    </i>
  </div>
);

/** 1. Пара «класс + предмет» в списке своих пар. */
export const PairCard: React.FC<{ pair: TeacherPair; onOpen: () => void }> = ({
  pair, onOpen,
}) => (
  <Tappable
    Component="div"
    onClick={onOpen}
    style={{
      background: 'var(--vkui--color_background_content)',
      border: '1px solid var(--vkui--color_separator_primary)',
      borderRadius: 14, padding: 12, marginBottom: 9,
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <SubjectAvatar subject={pair.subject} color={pair.subject_color} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <Text weight="2" style={{
          fontSize: 15, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          display: 'block',
        }}>
          {pair.subject} · {pair.batch}
        </Text>
        {pair.faculty && (
          <Caption style={{
            fontSize: 12, color: 'var(--vkui--color_text_secondary)',
            display: 'block', marginTop: 2,
          }}>
            {pair.faculty}
          </Caption>
        )}
      </div>
      <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
        <StatBlock value={fmtAvg(pair.average_mark)} label="средний" />
        <StatBlock value={`${Math.round(pair.attendance_rate)}%`} label="посещ." />
        <StatBlock value={String(pair.total_classes)} label="уроков" />
      </div>
    </div>
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      marginTop: 10, paddingTop: 9,
      borderTop: '1px solid var(--vkui--color_separator_primary)',
    }}>
      {/* Последние оценки пары — те же чипы, что везде (GradeChip).
          Счётчики 5/4/3/2 убраны по решению Миши: показываем оценки,
          детали — внутри. */}
      <GradeChips
        grades={pair.latest_grades.map(g => ({
          grade: g.grade,
          date: g.date,
        }))}
        withDate
      />
      <span style={{ marginLeft: 'auto', color: 'var(--vkui--color_icon_secondary)', fontSize: 19 }}>›</span>
    </div>
  </Tappable>
);

/** 2. Ученик пары — тап открывает карточку ученика. */
export const StudentRow: React.FC<{ student: PairStudent; onOpen: () => void }> = ({
  student, onOpen,
}) => {
  const parts = student.name.split(' ');
  const initials = (parts[0]?.[0] || '') + (parts[1]?.[0] || '');
  return (
    <Tappable
      Component="div"
      onClick={onOpen}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'var(--vkui--color_background_content)',
        borderRadius: 12, padding: '10px 12px', marginBottom: 8,
        boxShadow: '0 1px 3px rgba(0,0,0,.08)',
      }}
    >
      <div style={{
        width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
        background: 'var(--vkui--color_background_accent_tint)',
        color: 'var(--vkui--color_text_accent)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 700,
      }}>
        {initials}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Text style={{
          fontSize: 14, display: 'block',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {student.name}
        </Text>
        <Caption style={{ fontSize: 12, color: 'var(--vkui--color_text_secondary)' }}>
          <Text weight="2" style={{ color: 'var(--vkui--color_text_primary)' }}>
            {fmtAvg(student.average_mark)}
          </Text>
          {' · посещ. '}
          {Math.round(student.attendance_rate)}%
          {' · '}
          {student.total_classes}
          {' уроков'}
        </Caption>
      </div>
      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
        {student.latest_grades.length === 0
          ? <span style={{ fontSize: 12, color: 'var(--vkui--color_icon_secondary)' }}>—</span>
          : student.latest_grades.slice(0, 5).map((g, i) => (
            <GradeChip key={`${g}-${i}`} grade={g} />
          ))}
      </div>
    </Tappable>
  );
};

/** 3. Предмет в карточке ученика. mine=true — открывает детализацию,
 *  чужие предметы приглушены и помечены «только чтение». */
export const SubjectCard: React.FC<{
  subject: StudentSubjectCard;
  onOpen: () => void;
}> = ({ subject, onOpen }) => {
  const mine = subject.mine;
  return (
    <Tappable
      Component="div"
      onClick={mine ? onOpen : undefined}
      style={{
        background: mine
          ? 'var(--vkui--color_background_content)'
          : 'var(--vkui--color_background_secondary)',
        border: mine ? 'none' : '1px solid var(--vkui--color_separator_primary)',
        borderRadius: 14, padding: 12, marginBottom: 8,
        opacity: mine ? 1 : 0.75,
        boxShadow: mine ? '0 1px 3px rgba(0,0,0,.08)' : 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <SubjectAvatar subject={subject.name} color={subject.subject_color} muted={!mine} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text weight={mine ? '2' : '1'} style={{
            fontSize: 15, display: 'block', color: 'var(--vkui--color_text_primary)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {subject.name}
          </Text>
          <Caption style={{ fontSize: 12, color: 'var(--vkui--color_text_secondary)' }}>
            <Text weight="2" style={{ color: 'var(--vkui--color_text_primary)' }}>
              {fmtAvg(subject.average_mark)}
            </Text>
            {' · посещ. '}
            {Math.round(subject.attendance_rate)}%
            {' · '}
            {subject.total_classes}
            {' уроков'}
          </Caption>
        </div>
        {mine && (
          <span style={{
            marginLeft: 'auto', flexShrink: 0,
            background: 'var(--vkui--color_background_accent_tint)',
            color: 'var(--vkui--color_text_accent)',
            fontSize: 10, padding: '4px 8px', borderRadius: 10,
          }}>
            мой предмет
          </span>
        )}
      </div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        marginTop: 10, paddingTop: 9,
        borderTop: `1px solid ${mine
          ? 'var(--vkui--color_separator_primary)'
          : 'var(--vkui--color_separator_secondary)'}`,
      }}>
        <GradeChips grades={subject.latest_grades} withDate />
        {mine ? (
          <span style={{ marginLeft: 'auto', color: 'var(--vkui--color_icon_secondary)', fontSize: 19 }}>›</span>
        ) : (
          <span style={{
            marginLeft: 'auto', fontSize: 11, color: 'var(--vkui--color_text_secondary)',
          }}>
            только чтение
          </span>
        )}
      </div>
    </Tappable>
  );
};
