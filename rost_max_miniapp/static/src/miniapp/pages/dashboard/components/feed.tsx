// Лента дня (вариант A) — общие компоненты главной страницы.
// Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { SimpleCell, Text, Caption, Div, Counter, Placeholder, Card as VkCard, Avatar, Input, Button } from '@vkontakte/vkui';
import {
  Icon28ClockOutline,
  Icon56EventOutline,
} from '@vkontakte/icons';
import { LessonRow } from '@/shared/components/LessonRow';
import { TimedGroups } from '@/shared/components/TimedGroups';
import { initialsOf } from '@/shared/lib/initials';
import type { HomeworkSubmissionsResponse, HomeworkSubmissionStudent } from '@/shared/lib/types';

const WEEKDAYS = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];
const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

export const formatDateLong = (iso: string): string => {
  const d = new Date(iso + 'T00:00:00');
  if (isNaN(d.getTime())) return iso;
  return `${WEEKDAYS[d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth()]}`;
};

const startTimeOf = (timing: string): string => (timing || '').split(' - ')[0] || timing;

const fmtDue = (due: string): string => {
  if (!due) return '';
  const d = new Date(due);
  if (isNaN(d.getTime())) return due;
  return `до ${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}`;
};

// --- Карточка-заголовок (приветствие) -----------------------------------

// Имя-отчество: «Ермакова Лариса Анатольевна» -> «Лариса Анатольевна».
// Фамилию отбрасываем — обращение по имени, не фамильярно и не казённо.
const firstNamePatronymic = (full: string): string => {
  const parts = (full || '').trim().split(/\s+/);
  return parts.length >= 3 ? parts.slice(1).join(' ') : full;
};

// Ученик: «Макаров Михаил Игоревич» -> «Михаил» (второе слово ФИО).
// Учителю/админу — имя-отчество.
export const Greeting: React.FC<{ name: string; date: string; avatar?: string; short?: boolean }> = ({ name, date, avatar, short }) => {
  const parts = (name || '').trim().split(/\s+/);
  const display = short
    ? (parts.length >= 2 ? parts[1] : name)
    : firstNamePatronymic(name);
  return (
    <Div style={{ paddingBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Avatar
          size={48}
          mode="app"
          src={avatar || undefined}
          fallbackIcon={
            <span style={{ fontSize: 18, fontWeight: 600 }}>
              {initialsOf(display)}
            </span>
          }
          objectPosition="center top"
          style={{ borderRadius: 8, flexShrink: 0 }}
        />
        <div>
          <Text weight="2" style={{ fontSize: 20, display: 'block' }}>Привет, {display}</Text>
          {/* Зазор имя -> дата: ощутимый, даты придаточное предложение */}
          <Caption style={{ color: 'var(--vkui--color_text_secondary)', display: 'block', marginTop: 6 }}>
            {formatDateLong(date)}
          </Caption>
        </div>
      </div>
    </Div>
  );
};

export interface FeedLesson {
  id: number;
  sheet_id: number | null;
  subject: string;
  batch: string;
  faculty: string;
  faculty_avatar?: string;
  timing: string;
  is_now: boolean;
  journal_unfilled: boolean;
  homework: string;
}

/**
 * Карточка блока: заголовок ВНУТРИ карточки (строка с паддингом),
 * контент ниже. ВАЖНО: контент кладём напрямую в Card, без Group —
 * у .vkuiGroup__host:first-of-type в VKUI жёсткое
 * border-top-*-radius: 0, Group съедает верхнее скругление Card.
 * Обычный div ничего не ломает: Card c overflow:hidden сам режет
 * содержимое по своим скруглениям.
 */
const CardBlock: React.FC<{
  title: React.ReactNode;
  after?: React.ReactNode;
  children: React.ReactNode;
}> = ({ title, after, children }) => (
  <div style={{ margin: '0 8px 8px' }}>
    <VkCard mode="shadow" style={{ overflow: 'hidden' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px 8px',
      }}>
        {title}
        {after}
      </div>
      {children}
    </VkCard>
  </div>
);

/** Заголовок блока (без Header после рефакторинга — просто Text). */
const BlockTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Text weight="2">{children}</Text>
);

/** Ссылка «… →» справа от заголовка блока. */
const BlockLink: React.FC<{ onClick?: () => void; children: React.ReactNode }> = ({ onClick, children }) => (
  <span
    style={{ color: 'var(--vkui--color_text_accent)', fontWeight: 500, cursor: 'pointer', fontSize: 13 }}
    onClick={onClick}
  >
    {children}
  </span>
);

export const TodayLessons: React.FC<{
  lessons: FeedLesson[];
  onOpenJournal?: (sheetId: number) => void;
  onOpenTimetable?: () => void;
  showBatch?: boolean;
  /** Админ: слоты-аккордеоны по таймингу (в расписании вся школа). */
  grouped?: boolean;
}> = ({ lessons, onOpenJournal, onOpenTimetable, showBatch, grouped }) => (
  <CardBlock
    title={<BlockTitle>Сегодня · {lessons.length} {plural(lessons.length, 'урок', 'урока', 'уроков')}</BlockTitle>}
    after={onOpenTimetable ? <BlockLink onClick={onOpenTimetable}>Вся неделя →</BlockLink> : undefined}
  >
    {grouped ? (
      // Админ: слоты по таймингу, раскрыт текущий (как в расписании).
      <TimedGroups
        lessons={lessons}
        isToday
        resetKey={lessons[0]?.id != null ? 'dashboard' + lessons[0].id : 'dashboard'}
        onOpenLesson={onOpenJournal}
      />
    ) : (
      lessons.map(l => (
        // Строка урока общая с расписанием (LessonRow): аватар учителя,
        // время акцентом, класс в Counter справа, чипы «Журнал не заполнен» /
        // «Есть ДЗ» как в макете dashboard-teacher-admin.html.
        <LessonRow
          key={l.id}
          lesson={l}
          showBatch={showBatch}
          journalUnfilled={showBatch && l.journal_unfilled}
          hasHomework={Boolean(l.homework)}
          isNow={l.is_now}
          onClick={onOpenJournal && l.sheet_id ? () => onOpenJournal(l.sheet_id!) : undefined}
        />
      ))
    )}
  </CardBlock>
);

// --- Оценки за сегодня (ученик) ------------------------------------------

export interface GradeToday {
  grades: number[];
  subject: string;
  comment: string;
}

export const GradesToday: React.FC<{
  grades: GradeToday[];
  onOpenGrades?: () => void;
  average?: number | null;
}> = ({ grades, onOpenGrades, average }) => (
  <CardBlock
    title={<BlockTitle>Оценки за сегодня</BlockTitle>}
    after={onOpenGrades ? <BlockLink onClick={onOpenGrades}>Все оценки →</BlockLink> : undefined}
  >
    {grades.length === 0 ? (
      <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Оценок пока нет</Caption></Div>
    ) : (
      grades.map((g, i) => (
        <SimpleCell
          key={i}
          before={
            <span style={{
              width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontWeight: 700, fontSize: 14,
              background: Math.max(...g.grades) >= 4
                ? 'var(--vkui--color_background_positive)'
                : Math.max(...g.grades) === 3
                  ? 'var(--vkui--color_background_warning)'
                  : 'var(--vkui--color_background_negative)',
            }}>
              {g.grades.join(' ')}
            </span>
          }
          subtitle={g.comment || undefined}
        >
          {g.subject}
        </SimpleCell>
      ))
    )}
    {average != null && (
      <Div style={{ paddingTop: 4 }}>
        <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
          Средний балл за четверть: <Text weight="2" style={{ display: 'inline' }}>{average}</Text>
        </Caption>
      </Div>
    )}
  </CardBlock>
);

// --- Домашние задания (ученик) -------------------------------------------

export interface HomeworkItem {
  id: number;
  subject: string;
  task: string;
  due: string;
  overdue: boolean;
  /** none | draft | submit | reject | change | accept */
  state: string;
  answer_required: boolean;
  answer: string;
  teacher_note: string;
  submitted_at: string;
  late: boolean;
}

const HW_STATE_LABEL: Record<string, string> = {
  submit: 'Сдано',
  accept: 'Принято',
  change: 'На доработку',
  reject: 'Отклонено',
};

export const HomeworkList: React.FC<{
  items: HomeworkItem[];
  canSubmit?: boolean;
  onSubmit?: (id: number, answer: string) => Promise<string | null>;
  onUpdated?: () => void;
}> = ({ items, canSubmit, onSubmit, onUpdated }) => {
  const [expandedId, setExpandedId] = React.useState<number | null>(null);
  const [answer, setAnswer] = React.useState('');
  const [busy, setBusy] = React.useState(false);

  const open = (h: HomeworkItem) => {
    setExpandedId(prev => (prev === h.id ? null : h.id));
    setAnswer(h.state === 'none' || h.state === 'change' ? (h.answer || '') : '');
  };

  const send = async (h: HomeworkItem) => {
    if (!onSubmit) return;
    setBusy(true);
    const err = await onSubmit(h.id, answer.trim());
    setBusy(false);
    if (err === null) {
      setExpandedId(null);
      onUpdated?.();
    }
  };

  return (
    <CardBlock title={<BlockTitle>Домашние задания</BlockTitle>}>
      {items.length === 0 ? (
        <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Заданий нет — можно отдыхать</Caption></Div>
      ) : (
        items.map(h => {
          const label = HW_STATE_LABEL[h.state];
          const expanded = expandedId === h.id;
          return (
            <div key={h.id} style={{ borderTop: '1px solid var(--vkui--color_background_secondary)' }}>
              <SimpleCell
                onClick={() => open(h)}
                before={
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 2,
                    background: h.state === 'accept' || h.state === 'submit'
                      ? 'var(--vkui--color_background_positive)'
                      : 'var(--vkui--color_background_negative)',
                  }} />
                }
                after={
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {label && (
                      <Counter mode={h.state === 'accept' ? 'positive' : h.state === 'change' ? 'warning' : 'primary'}>
                        {label}
                      </Counter>
                    )}
                    {h.overdue && (h.state === 'none' || h.state === 'change') && (
                      <Counter mode="primary">Просрочено</Counter>
                    )}
                  </div>
                }
                subtitle={[
                  fmtDue(h.due),
                  h.late && h.state !== 'none' ? 'сдано с опозданием' : '',
                  h.task.length > 80 ? h.task.slice(0, 80) + '…' : h.task,
                ].filter(Boolean).join(' · ') || undefined}
              >
                {h.subject}
              </SimpleCell>

              {expanded && (
                <div style={{ padding: '0 16px 12px' }}>
                  <Caption style={{
                    color: 'var(--vkui--color_text_secondary)',
                    display: 'block', whiteSpace: 'pre-wrap', marginBottom: 8,
                  }}>
                    {h.task}
                  </Caption>

                  {h.state === 'change' && h.teacher_note && (
                    <Caption style={{
                      color: 'var(--vkui--color_text_warning)',
                      display: 'block', marginBottom: 8,
                    }}>
                      Учитель: {h.teacher_note}
                    </Caption>
                  )}

                  {h.answer_required && h.answer && h.state !== 'change' && (
                    <Caption style={{
                      color: 'var(--vkui--color_text_secondary)',
                      display: 'block', marginBottom: 8,
                    }}>
                      Ваш ответ: {h.answer}
                    </Caption>
                  )}

                  {canSubmit && (h.state === 'none' || h.state === 'draft' || h.state === 'change' || h.state === 'reject') ? (
                    <>
                      {h.answer_required && (
                        <Input
                          value={answer}
                          onChange={e => setAnswer(e.target.value)}
                          placeholder="Ваш ответ"
                          aria-label="Ответ на задание"
                          style={{ marginBottom: 8 }}
                        />
                      )}
                      <Button
                        size="s"
                        stretched
                        loading={busy}
                        disabled={h.answer_required && !answer.trim()}
                        onClick={() => send(h)}
                      >
                        Сдать
                      </Button>
                    </>
                  ) : (
                    h.state === 'submit' && (
                      <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
                        Ждёт проверки учителя
                      </Caption>
                    )
                  )}
                </div>
              )}
            </div>
          );
        })
      )}
    </CardBlock>
  );
};

// --- Журналы к заполнению (учитель) ---------------------------------------

export interface JournalToFill {
  sheet_id: number;
  subject: string;
  batch: string;
  timing: string;
  room: string;
  students: number;
}

export const JournalsToFill: React.FC<{
  items: JournalToFill[];
  onOpenJournal: (sheetId: number) => void;
}> = ({ items, onOpenJournal }) => (
  <CardBlock title={<BlockTitle>Журналы к заполнению</BlockTitle>}>
    {items.length === 0 ? (
      <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Все журналы заполнены 👍</Caption></Div>
    ) : (
      items.map(j => (
        <SimpleCell
          key={j.sheet_id}
          onClick={() => onOpenJournal(j.sheet_id)}
          after={<Counter mode="primary">Заполнить</Counter>}
          subtitle={`${startTimeOf(j.timing)} · ${j.room} · ${j.students} ${plural(j.students, 'ученик', 'ученика', 'учеников')}`}
        >
          {`${j.batch} · ${j.subject}`}
        </SimpleCell>
      ))
    )}
  </CardBlock>
);

// --- Задано моими уроками (учитель) ---------------------------------------

export interface MyHomeworkItem {
  id: number;
  subject: string;
  batch: string;
  task: string;
  due: string;
  submitted: number;
  total: number;
  /** Сдач в состоянии submit (ждут проверки учителя). */
  to_review: number;
}

export const MyHomework: React.FC<{ items: MyHomeworkItem[]; onOpen?: (id: number) => void }> = ({ items, onOpen }) => (
  <CardBlock title={<BlockTitle>Домашние задания</BlockTitle>}>
    {items.length === 0 ? (
      <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Активных заданий нет</Caption></Div>
    ) : (
      items.map(h => (
        <SimpleCell
          key={h.id}
          onClick={onOpen ? () => onOpen(h.id) : undefined}
          before={
            <span style={{
              width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 2,
              background: h.submitted >= h.total && h.total > 0
                ? 'var(--vkui--color_background_positive)'
                : 'var(--vkui--color_background_negative)',
            }} />
          }
          after={
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              {h.to_review > 0 && (
                <Counter mode="accent">{`${h.to_review} к проверке`}</Counter>
              )}
              <Counter mode="primary">{`Сдали ${h.submitted} из ${h.total}`}</Counter>
            </div>
          }
          subtitle={[
            `${h.batch} · ${fmtDue(h.due)}`,
            h.task.length > 70 ? h.task.slice(0, 70) + '…' : h.task,
          ].filter(Boolean).join(' · ') || undefined}
        >
          {h.subject}
        </SimpleCell>
      ))
    )}
  </CardBlock>
);

// --- Сдачи по заданию (учитель: проверка) ----------------------------------

export const STATE_LABEL: Record<string, string> = {
  submit: 'Сдано',
  accept: 'Принято',
  change: 'На доработку',
  reject: 'Отклонено',
  none: 'Не сдал',
  draft: 'Черновик',
};

export const SubmissionReviewCard: React.FC<{
  submission: HomeworkSubmissionsResponse;
  onClose: () => void;
  onReview: (subId: number, action: 'accept' | 'change', note: string) => Promise<string | null>;
  onUpdated?: () => void;
}> = ({ submission, onClose, onReview, onUpdated }) => {
  const { assignment, students } = submission;
  const [busyId, setBusyId] = React.useState<number | null>(null);
  const [notes, setNotes] = React.useState<Record<number, string>>({});

  const review = async (student: HomeworkSubmissionStudent, action: 'accept' | 'change') => {
    setBusyId(student.student_id);
    const err = await onReview(student.student_id, action, (notes[student.student_id] || '').trim());
    setBusyId(null);
    if (err === null) onUpdated?.();
  };

  const submittedCount = students.filter(s => s.state === 'submit' || s.state === 'accept').length;

  return (
    <Div style={{ paddingInline: 8 }}>
      <VkCard mode="shadow" style={{ overflow: 'hidden', marginBottom: 8 }}>
        <div style={{ padding: '12px 16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <Text weight="2">{assignment.subject} — сдачи</Text>
            <span
              style={{ color: 'var(--vkui--color_text_accent)', cursor: 'pointer', fontSize: 13 }}
              onClick={onClose}
            >
              Закрыть
            </span>
          </div>
          <Caption style={{ color: 'var(--vkui--color_text_secondary)', display: 'block' }}>
            {assignment.task.length > 120 ? assignment.task.slice(0, 120) + '…' : assignment.task}
          </Caption>
          <Caption style={{ color: 'var(--vkui--color_text_secondary)', display: 'block', marginTop: 4 }}>
            Сдали {submittedCount} из {students.length}
            {assignment.answer_required ? ' · требуется ответ' : ''}
          </Caption>
        </div>

        {students.map(s => {
          const subId = s.student_id;
          const canReview = s.state === 'submit';
          return (
            <div key={s.student_id} style={{ borderTop: '1px solid var(--vkui--color_background_secondary)', padding: '10px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text weight="2">{s.name}</Text>
                <Counter
                  mode={s.state === 'accept' ? 'positive' : s.state === 'change' ? 'warning' : s.state === 'submit' ? 'accent' : 'primary'}
                >
                  {STATE_LABEL[s.state] || s.state}
                </Counter>
              </div>
              {s.late && s.state !== 'none' && (
                <Caption style={{ color: 'var(--vkui--color_text_warning)', display: 'block', marginTop: 2 }}>
                  сдано с опозданием
                </Caption>
              )}
              {s.answer && (
                <Caption style={{
                  color: 'var(--vkui--color_text_secondary)',
                  display: 'block', marginTop: 4, whiteSpace: 'pre-wrap',
                }}>
                  Ответ: {s.answer}
                </Caption>
              )}
              {canReview && (
                <>
                  <Input
                    value={notes[subId] || ''}
                    onChange={e => setNotes(prev => ({ ...prev, [subId]: e.target.value }))}
                    placeholder="Комментарий (для доработки)"
                    aria-label="Комментарий учителя"
                    style={{ marginTop: 6 }}
                  />
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <Button
                      size="s"
                      appearance="positive"
                      loading={busyId === subId}
                      onClick={() => review(s, 'accept')}
                    >
                      Принять
                    </Button>
                    <Button
                      size="s"
                      mode="outline"
                      appearance="negative"
                      disabled={busyId === subId}
                      onClick={() => review(s, 'change')}
                    >
                      На доработку
                    </Button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </VkCard>
    </Div>
  );
};

// --- Полоса цифр + требует внимания (админ) --------------------------------

export interface AdminStats {
  lessons_today: number;
  batches_today: number;
  journals_unfilled: number;
}

export const AdminStatStrip: React.FC<{ stats: AdminStats }> = ({ stats }) => {
  const tiles = [
    { num: stats.lessons_today, label: ['уроков сегодня', `${stats.batches_today} классов`] },
    { num: stats.journals_unfilled, label: ['журналов', 'не заполнено'], bad: stats.journals_unfilled > 0 },
  ];
  return (
    <Div style={{ display: 'flex', gap: 8, paddingInline: 8 }}>
      {tiles.map((t, i) => (
        <div key={i} style={{
          flex: 1,
          background: 'var(--vkui--color_background_content)',
          borderRadius: 12,
          padding: '10px 12px',
        }}>
          <Text weight="2" style={{
            fontSize: 24,
            color: t.bad ? 'var(--vkui--color_text_negative)' : undefined,
          }}>{t.num}</Text>
          <Caption style={{ color: 'var(--vkui--color_text_secondary)', display: 'block', lineHeight: 1.3 }}>
            {t.label[0]}<br />{t.label[1]}
          </Caption>
        </div>
      ))}
    </Div>
  );
};

export const AdminAlerts: React.FC<{ unfilled: number; morningPassed: number }> = ({ unfilled, morningPassed }) => (
  <CardBlock title={<BlockTitle>Требует внимания</BlockTitle>}>
    {unfilled > 0 ? (
      <SimpleCell
        before={<Icon28ClockOutline />}
        subtitle={morningPassed > 0
          ? `из них ${morningPassed} — уроки до обеда уже прошли`
          : 'все ещё идут или впереди'}
      >
        {`${unfilled} ${plural(unfilled, 'журнал', 'журнала', 'журналов')} не заполнено`}
      </SimpleCell>
    ) : (
      <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Всё в порядке</Caption></Div>
    )}
  </CardBlock>
);

// --- Пустой день ------------------------------------------------------------

export const EmptyDay: React.FC<{ date: string }> = ({ date }) => (
  <Placeholder icon={<Icon56EventOutline />} title="Уроков нет">
    {formatDateLong(date)} — выходной или каникулы.
  </Placeholder>
);

// --- utils ------------------------------------------------------------------

export function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}
