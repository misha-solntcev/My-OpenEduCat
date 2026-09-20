/**
 * Очередь проверки сдач — вариант D (design/hw-review-redesign-variants.html).
 * Сегмент «Проверить / На доработке / Проверено» — рабочие фильтры: каждый
 * показывает свой список; сдача из «Проверить» раскрыта (ответ, вложения,
 * комментарий, Принять/На доработку/оценка), тап по строке переключает
 * раскрытие. «На доработке» и «Проверено» — компактные строки (у «На
 * доработке» в подстроке последний комментарий учителя, у «Проверено» —
 * бейдж оценки как в журнале).
 */
import React from 'react';
import { Avatar, Button, Caption, Input, Text } from '@vkontakte/vkui';
import { initialsOf } from '@/shared/lib/initials';
import { AccentSegmentedControl } from '@/shared/components/AccentSegmentedControl';
import {
  Icon24ListCheckOutline, Icon24ChevronRight, Icon28AttachOutline,
} from '@vkontakte/icons';
import { JournalButton } from '@/shared/components/JournalButton';
import type { HomeworkSubmissionsResponse, HomeworkSubmissionStudent } from '@/shared/lib/types';

/* --- тон бейджа оценки (как в журнале/карточке ученика): цветной тинт +
       рамка, текст text_primary (цветной текст на своём тинте не читается) */
const markTone = (mark: number | null): React.CSSProperties => {
  const map: Record<number, { bg: string; border: string }> = {
    5: { bg: 'var(--vkui--color_background_positive_tint)', border: 'var(--vkui--color_stroke_positive)' },
    4: { bg: 'var(--vkui--color_background_accent_tint)', border: 'var(--vkui--color_stroke_accent)' },
    3: { bg: 'var(--vkui--color_background_warning)', border: 'var(--vkui--color_icon_warning)' },
    2: { bg: 'var(--vkui--color_background_negative_tint)', border: 'var(--vkui--color_stroke_negative)' },
  };
  const tone = mark != null ? map[mark] : undefined;
  return {
    width: 36, height: 36, borderRadius: 10, flexShrink: 0,
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 17, fontWeight: 700,
    background: tone?.bg ?? 'var(--vkui--color_background_secondary)',
    border: `1px solid ${tone?.border ?? 'var(--vkui--color_separator_primary)'}`,
    color: 'var(--vkui--color_text_primary)',
  };
};

/* янтарная плашка «На доработке» (AmberChip: warning-тинта текста нет в VKUI 8) */
const amberPill: React.CSSProperties = {
  fontSize: 11, fontWeight: 600, padding: '4px 8px', borderRadius: 8,
  whiteSpace: 'nowrap', flexShrink: 0,
  background: 'var(--vkui--color_background_warning)',
  border: '1px solid var(--vkui--color_icon_warning)',
  color: 'var(--vkui--color_text_primary)',
};
const grayPill: React.CSSProperties = {
  fontSize: 11, fontWeight: 600, padding: '4px 8px', borderRadius: 8,
  whiteSpace: 'nowrap', flexShrink: 0,
  background: 'var(--vkui--color_background_secondary)',
  color: 'var(--vkui--color_text_secondary)',
};

type SegKey = 'submit' | 'change' | 'checked';

const SEG_TITLES: Record<SegKey, string> = {
  submit: 'Проверить',
  change: 'На доработке',
  checked: 'Проверено',
};

/** Дата сдачи «сегодня/вчера в 15:32» либо «12 сен». */
const fmtSubmittedAt = (iso: string): string => {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const now = new Date();
  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  const yest = new Date(now); yest.setDate(now.getDate() - 1);
  const day = sameDay(d, now) ? 'сегодня'
    : sameDay(d, yest) ? 'вчера'
      : `${d.getDate()} сен`;
  return `сдал ${day} в ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

export const ReviewQueue: React.FC<{
  submission: HomeworkSubmissionsResponse;
  onReview: (subId: number, action: 'accept' | 'change', note: string, mark: number | null) => Promise<string | null>;
}> = ({ submission, onReview }) => {
  const { students } = submission;
  const [seg, setSeg] = React.useState<SegKey>('submit');
  const [busyId, setBusyId] = React.useState<number | null>(null);
  const [notes, setNotes] = React.useState<Record<number, string>>({});
  const [marks, setMarks] = React.useState<Record<number, number | null>>({});
  // undefined = юзер ещё не тапал (авто-раскрыта первая строка),
  // null = закрыл руками, число = открытая строка.
  const [expanded, setExpanded] = React.useState<number | null | undefined>(undefined);

  // «Проверить» = ждущие проверки (submit); не сдавшие показываются в этом
  // же списке ниже, серым «Не сдано». Сдача на доработке — только в
  // «На доработке», принятая — только в «Проверено» (непересекающиеся).
  const bySeg = React.useMemo(() => ({
    submit: [
      ...students.filter(s => s.state === 'submit'),
      ...students.filter(s => s.state === 'none' || s.state === 'draft'),
    ],
    change: students.filter(s => s.state === 'change'),
    checked: students.filter(s => s.state === 'accept' || s.state === 'reject'),
  }), [students]);

  const rows = bySeg[seg];

  // при смене сегмента возвращаем авто-раскрытие первой строки
  React.useEffect(() => { setExpanded(undefined); }, [seg]);

  const review = async (s: HomeworkSubmissionStudent, action: 'accept' | 'change') => {
    setBusyId(s.student_id);
    // Оценка — кнопкой журнала (цикл — → 5 → 4 → 3 → 2 → —), только при «Принять».
    const mark = action === 'accept' ? (marks[s.student_id] ?? null) : null;
    const err = await onReview(s.sub_id ?? s.student_id, action,
      (notes[s.student_id] || '').trim(), mark);
    setBusyId(null);
    return err;
  };

  return (
    <div style={{ paddingInline: 8 }}>
      {/* сегмент-фильтры (общий AccentSegmentedControl). */}
      <AccentSegmentedControl
        aria-label="Состояния сдач"
        value={seg}
        onChange={setSeg}
        style={{ margin: '10px 0 10px' }}
        options={(Object.keys(SEG_TITLES) as SegKey[]).map(key => ({
          value: key, title: SEG_TITLES[key], count: bySeg[key].length,
        }))}
      />

      <div style={{
        background: 'var(--vkui--color_background_content)',
        borderRadius: 'var(--vkui--size_card_border_radius--regular)',
        boxShadow: 'var(--vkui--elevation1)', margin: '6px 0 8px', overflow: 'hidden',
      }}>
        {rows.length === 0 && (
          <Caption style={{ display: 'block', padding: '16px 12px', color: 'var(--vkui--color_text_secondary)' }}>
            Здесь пока пусто
          </Caption>
        )}

        {rows.map((s, idx) => {
          const subId = s.student_id;
          // тап раскрывает детали сдачи: в «Проверить» — только ждущие
          // (несдавшие раскрывать нечего), в «На доработке» — все строки.
          const tapOpen = seg === 'change'
            || s.state === 'submit' || s.state === 'accept' || s.state === 'reject';
          const open = tapOpen
            && (expanded === undefined
              ? idx === rows.findIndex(_r => tapOpen)
              : expanded === subId);
          const chevron = tapOpen ? (
            <span style={{ color: 'var(--vkui--color_text_secondary)', flexShrink: 0, display: 'flex' }}>
              <Icon24ChevronRight
                style={{ transform: open ? 'rotate(90deg)' : undefined, transition: 'transform .15s' }}
              />
            </span>
          ) : null;
          return (
            <React.Fragment key={s.student_id}>
              {/* строка ученика */}
              <div
                role={tapOpen ? 'button' : undefined}
                tabIndex={tapOpen ? 0 : undefined}
                onClick={tapOpen ? () => setExpanded(open ? null : subId) : undefined}
                onKeyDown={tapOpen ? (e => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setExpanded(open ? null : subId);
                  }
                }) : undefined}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 12px', cursor: tapOpen ? 'pointer' : 'default',
                  borderTop: idx > 0 ? '1px solid var(--vkui--color_separator_primary)' : undefined,
                }}
              >
                <Avatar
                  size={40}
                  initials={initialsOf(s.name)}
                  src={s.avatar || undefined}
                  objectPosition="center top"
                  style={{ borderRadius: 8, flexShrink: 0 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text weight="2" style={{
                    fontSize: 15, lineHeight: '20px',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {s.name}
                  </Text>
                  <Caption style={{
                    display: 'block', fontSize: 12, color: 'var(--vkui--color_text_secondary)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {s.state === 'submit' && fmtSubmittedAt(s.submitted_at)}
                    {s.state === 'change' && (s.teacher_note
                      ? `ваш комментарий: «${s.teacher_note}»` : 'отправлен на доработку')}
                    {s.state === 'accept' && (s.mark ? `принято${s.submitted_at ? ` · ${fmtSubmittedAt(s.submitted_at).replace('сдал ', '')}` : ''}` : 'принято')}
                    {s.state === 'reject' && 'отклонено'}
                    {(s.state === 'none' || s.state === 'draft') && 'Не сдано'}
                  </Caption>
                </div>
                {s.state === 'accept' && <span style={markTone(s.mark)}>{s.mark ?? '—'}</span>}
                {s.state === 'submit' && <span style={grayPill}>На проверке</span>}
                {s.state === 'change' && <span style={amberPill}>На доработке</span>}
                {s.state === 'reject' && (
                  <span style={{
                    ...grayPill,
                    background: 'var(--vkui--color_background_negative_tint)',
                    border: '1px solid var(--vkui--color_stroke_negative)',
                  }}>Отклонено</span>
                )}
                {chevron}
              </div>

              {/* раскрытая проверка (мокап: .chk) */}
              {open && (
                <div style={{
                  borderTop: '1px solid var(--vkui--color_separator_primary)',
                  padding: '10px 12px',
                  background: 'var(--vkui--color_background_secondary)',
                }}>
                  {s.answer && (
                    <div style={{
                      background: 'var(--vkui--color_background_content)',
                      border: '1px solid var(--vkui--color_separator_primary)',
                      borderRadius: 10, padding: '10px 12px',
                    }}>
                      <Caption style={{
                        display: 'flex', alignItems: 'center', gap: 5,
                        fontSize: 11, fontWeight: 600, letterSpacing: '.4px',
                        textTransform: 'uppercase', color: 'var(--vkui--color_text_secondary)',
                      }}>
                        <Icon24ListCheckOutline width={16} height={16} />
                        Ответ
                      </Caption>
                      <Text style={{
                        display: 'block', marginTop: 3, fontSize: 14,
                        lineHeight: '20px', whiteSpace: 'pre-wrap',
                        overflowWrap: 'anywhere',
                      }}>
                        {s.answer}
                      </Text>
                    </div>
                  )}
                  {s.attachments.length > 0 && (
                    <div style={{ marginTop: 6 }}>
                      {s.attachments.map(a => (
                        <a
                          key={a.url}
                          href={a.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            color: 'var(--vkui--color_text_accent)',
                            textDecoration: 'none', paddingBlock: 3,
                          }}
                        >
                          <Icon28AttachOutline width={16} height={16} />
                          <Caption>{a.name}</Caption>
                        </a>
                      ))}
                    </div>
                  )}
                  <Input
                    value={notes[subId] || ''}
                    onChange={e => setNotes(prev => ({ ...prev, [subId]: e.target.value }))}
                    placeholder="Комментарий — видит только ученик"
                    aria-label="Комментарий учителя"
                    style={{ marginTop: 8 }}
                  />
                  <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
                    <Button
                      size="s" stretched
                      loading={busyId === subId}
                      onClick={() => review(s, 'accept')}
                    >
                      Принять
                    </Button>
                    <Button
                      size="s" mode="outline" stretched
                      disabled={busyId === subId}
                      style={{
                        color: 'var(--vkui--color_icon_warning)',
                        border: '1px solid var(--vkui--color_icon_warning)',
                      }}
                      onClick={() => review(s, 'change')}
                    >
                      На доработку
                    </Button>
                    <JournalButton
                      kind="grade"
                      value={marks[subId] ?? null}
                      onCycle={next => setMarks(prev => ({ ...prev, [subId]: next }))}
                      title="Оценка за домашнее задание"
                    />
                  </div>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
