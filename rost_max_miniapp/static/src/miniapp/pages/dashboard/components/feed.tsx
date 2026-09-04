// Лента дня (вариант A) — общие компоненты главной страницы.
// Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { SimpleCell, Text, Caption, Div, Counter, Placeholder, Card as VkCard } from '@vkontakte/vkui';
import {
  Icon28ClockOutline,
  Icon56EventOutline,
} from '@vkontakte/icons';
import { LessonRow } from '@/shared/components/LessonRow';
import { TimedGroups } from '@/shared/components/TimedGroups';

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
export const Greeting: React.FC<{ name: string; date: string; short?: boolean }> = ({ name, date, short }) => {
  const parts = (name || '').trim().split(/\s+/);
  const display = short
    ? (parts.length >= 2 ? parts[1] : name)
    : firstNamePatronymic(name);
  return (
    <Div style={{ paddingBottom: 4 }}>
      <Text weight="2" style={{ fontSize: 20 }}>Привет, {display}</Text>
      <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>{formatDateLong(date)}</Caption>
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
  <div style={{ margin: '8px 8px' }}>
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
  done: boolean;
}

export const HomeworkList: React.FC<{ items: HomeworkItem[] }> = ({ items }) => (
  <CardBlock title={<BlockTitle>Домашние задания</BlockTitle>}>
    {items.length === 0 ? (
      <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Заданий нет — можно отдыхать</Caption></Div>
    ) : (
      items.map(h => (
        <SimpleCell
          key={h.id}
          before={
            <span style={{
              width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 2,
              background: h.done
                ? 'var(--vkui--color_background_positive)'
                : 'var(--vkui--color_background_negative)',
            }} />
          }
          after={h.overdue && !h.done ? <Counter mode="primary">Просрочено</Counter> : undefined}
          subtitle={[
            fmtDue(h.due),
            h.task.length > 80 ? h.task.slice(0, 80) + '…' : h.task,
          ].filter(Boolean).join(' · ') || undefined}
        >
          {h.subject}
        </SimpleCell>
      ))
    )}
  </CardBlock>
);

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
}

export const MyHomework: React.FC<{ items: MyHomeworkItem[] }> = ({ items }) => (
  <CardBlock title={<BlockTitle>Домашние задания</BlockTitle>}>
    {items.length === 0 ? (
      <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Активных заданий нет</Caption></Div>
    ) : (
      items.map(h => (
        <SimpleCell
          key={h.id}
          before={
            <span style={{
              width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 2,
              background: h.submitted >= h.total && h.total > 0
                ? 'var(--vkui--color_background_positive)'
                : 'var(--vkui--color_background_negative)',
            }} />
          }
          after={<Counter mode="primary">{`Сдали ${h.submitted} из ${h.total}`}</Counter>}
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
