// Лента дня (вариант A) — общие компоненты главной страницы.
// Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { Accordion, SimpleCell, Text, Caption, Div, Counter, Placeholder, Card as VkCard, Avatar, Input, Button } from '@vkontakte/vkui';
import {
  Icon28ClockOutline,
  Icon56EventOutline,
  Icon28AttachOutline,
} from '@vkontakte/icons';
import { TimedGroups } from '@/shared/components/TimedGroups';
import { JournalButton } from '@/shared/components/JournalButton';
import { TodayTimeline } from './TodayTimeline';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { initialsOf } from '@/shared/lib/initials';
import type {
  FeedLesson,
  HomeworkSubmissionsResponse,
  HomeworkSubmissionStudent,
} from '@/shared/lib/types';

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
export const Greeting: React.FC<{ name: string; date: string; avatar?: string; short?: boolean; onOpenProfile?: () => void }> = ({ name, date, avatar, short, onOpenProfile }) => {
  const parts = (name || '').trim().split(/\s+/);
  const display = short
    ? (parts.length >= 2 ? parts[1] : name)
    : firstNamePatronymic(name);
  return (
    <Div style={{ paddingBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Avatar
          size={48}
          src={avatar || undefined}
          fallbackIcon={
            <span style={{ fontSize: 18, fontWeight: 600 }}>
              {initialsOf(display)}
            </span>
          }
          objectPosition="center top"
          style={{
            borderRadius: 8, flexShrink: 0,
            cursor: onOpenProfile ? 'pointer' : undefined,
          }}
          onClick={onOpenProfile}
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

// FeedLesson общий, из shared/lib/types (с room/start/end для таймлайна).
export type { FeedLesson } from '@/shared/lib/types';

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
    title={<BlockTitle>Расписание на сегодня <Text weight="1" style={{ color: 'var(--vkui--color_text_secondary)' }}>· {lessons.length} {plural(lessons.length, 'урок', 'урока', 'уроков')}</Text></BlockTitle>}
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
      // Ученик/родитель/учитель: таймлайн дня с акцентом-состоянием
      // (этап 2 редизайна). Учитель без grouped — свои уроки подряд.
      <TodayTimeline
        lessons={lessons}
        showBatch={showBatch}
        onOpenJournal={onOpenJournal}
      />
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
    title={<BlockTitle>Последние оценки</BlockTitle>}
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
// Список с раскрытием и сдачей переехал в общий компонент: его же
// переиспользует вкладка «Задания» (редизайн, этап 1).

export type { HomeworkItem } from '@/shared/lib/types';
export { fmtDue } from '@/shared/components/HomeworkCardList';

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
  answer_required: boolean;
  materials_count: number;
  /** Админ-лента: имя преподавателя для группировки по учителям. */
  faculty?: string;
}

/** Группировка ДЗ по ключу (сохраняя порядок прихода с сервера). */
const groupByKey = (
  items: MyHomeworkItem[],
  keyOf: (h: MyHomeworkItem) => string,
): { key: string; items: MyHomeworkItem[] }[] => {
  const groups: { key: string; items: MyHomeworkItem[] }[] = [];
  const index = new Map<string, { key: string; items: MyHomeworkItem[] }>();
  for (const h of items) {
    const key = keyOf(h) || '';
    let g = index.get(key);
    if (!g) {
      g = { key, items: [] };
      index.set(key, g);
      groups.push(g);
    }
    g.items.push(h);
  }
  return groups;
};

const pluralRu = (n: number): string => {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return 'задание';
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'задания';
  return 'заданий';
};

const HomeworkGroup: React.FC<{
  title: string;
  items: MyHomeworkItem[];
  defaultExpanded: boolean;
  /** Скрывать ключ группы в строке (он уже в заголовке аккордеона). */
  hideKeyInRow?: boolean;
  onOpen?: (id: number) => void;
}> = ({ title, items, defaultExpanded, hideKeyInRow, onOpen }) => {
  const [expanded, setExpanded] = React.useState(defaultExpanded);
  const toReview = items.reduce((s, h) => s + h.to_review, 0);
  return (
    <Accordion expanded={expanded} onChange={setExpanded}>
      <Accordion.Summary
        after={
          // Flex с зазором: без него бейдж «к проверке» прилипает к счётчику.
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {toReview > 0 && <Counter mode="primary" appearance="accent">{`${toReview} к проверке`}</Counter>}
            <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
              {items.length} {pluralRu(items.length)}
            </Caption>
          </div>
        }
      >
        <Text weight="2">{title}</Text>
      </Accordion.Summary>
      <Accordion.Content>
        {items.map(h => <HomeworkRow key={h.id} h={h} hideKey={hideKeyInRow} onOpen={onOpen} />)}
      </Accordion.Content>
    </Accordion>
  );
};

const HomeworkRow: React.FC<{
  h: MyHomeworkItem;
  onOpen?: (id: number) => void;
  /** Ключ группировки уже в заголовке аккордеона — не дублируем. */
  hideKey?: boolean;
}> = ({ h, onOpen, hideKey }) => (
  <div style={{ borderBottom: '1px solid var(--vkui--color_background_secondary)' }}>
    <SimpleCell
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
            <Counter mode="primary" appearance="accent">{`${h.to_review} к проверке`}</Counter>
          )}
          <Counter mode="primary">{`Сдали ${h.submitted} из ${h.total}`}</Counter>
        </div>
      }
      subtitle={[
        hideKey ? fmtDue(h.due) : `${h.batch} · ${fmtDue(h.due)}`,
        h.task.length > 70 ? h.task.slice(0, 70) + '…' : h.task,
      ].filter(Boolean).join(' · ') || undefined}
    >
      {h.subject}
    </SimpleCell>
    <div style={{ padding: '0 16px 10px' }}>
      <MaterialsEditor assignmentId={h.id} />
    </div>
  </div>
);

export const MyHomework: React.FC<{
  items: MyHomeworkItem[];
  onOpen?: (id: number) => void;
  /** Админ: все ДЗ школы, аккордеон по учителям. */
  groupBy?: 'faculty' | 'batch';
}> = ({ items, onOpen, groupBy }) => (
  <CardBlock title={<BlockTitle>Домашние задания</BlockTitle>}>
    {items.length === 0 ? (
      <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Активных заданий нет</Caption></Div>
    ) : groupBy === 'faculty' ? (
      groupByKey(items, h => h.faculty || '').map(g => (
        <HomeworkGroup
          key={g.key}
          title={g.key}
          items={g.items}
          defaultExpanded={false}
          onOpen={onOpen}
        />
      ))
    ) : groupBy === 'batch' ? (
      groupByKey(items, h => h.batch).map(g => (
        <HomeworkGroup
          key={g.key}
          title={g.key}
          items={g.items}
          defaultExpanded={false}
          hideKeyInRow
          onOpen={onOpen}
        />
      ))
    ) : (
      items.map(h => <HomeworkRow key={h.id} h={h} onOpen={onOpen} />)
    )}
  </CardBlock>
);

// --- Сдачи по заданию (учитель: проверка) ----------------------------------

export const STATE_LABEL: Record<string, string> = {
  submit: 'На проверке',
  accept: 'Принято',
  change: 'На доработку',
  reject: 'Отклонено',
  none: 'Не сдал',
  draft: 'Черновик',
};

export const SubmissionReviewCard: React.FC<{
  submission: HomeworkSubmissionsResponse;
  onClose: () => void;
  onReview: (subId: number | null, action: 'accept' | 'change', note: string, mark: number | null, studentId: number) => Promise<string | null>;
  onUpdated?: () => void;
  // onClose остаётся в пропсах для совместимости вызовов, но не используется:
  // шапку с дублем информации (предмет/текст/счётчик) и нерабочей «Закрыть»
  // убрали — всё это уже есть на экране задания выше.
}> = ({ submission, onClose: _onClose, onReview, onUpdated }) => {
  const { students } = submission;
  const [busyId, setBusyId] = React.useState<number | null>(null);
  const [notes, setNotes] = React.useState<Record<number, string>>({});
  const [marks, setMarks] = React.useState<Record<number, number | null>>({});

  const review = async (student: HomeworkSubmissionStudent, action: 'accept' | 'change') => {
    setBusyId(student.student_id);
    // Оценка выбирается кнопкой журнала (цикл — → 5 → 4 → 3 → 2 → —);
    // ставится только при «Принять».
    const mark = action === 'accept' ? (marks[student.student_id] ?? null) : null;
    // sub_id = id строки сдачи — его ждёт /review, НЕ student_id.
    // sub_id === null — приём без сдачи (ответ устно/в тетради):
    // caller шлёт student_id на /homework/<id>/review_student.
    const err = await onReview(student.sub_id ?? null, action,
      (notes[student.student_id] || '').trim(), mark, student.student_id);
    setBusyId(null);
    if (err === null) onUpdated?.();
  };

  return (
    <Div style={{ paddingInline: 8 }}>
      <VkCard mode="shadow" style={{ overflow: 'hidden', marginBottom: 8 }}>
        {students.map(s => {
          const subId = s.student_id;
          // Принимаем сдавших и несдавших (приём без сдачи — устно/в тетради).
          const canReview = s.state === 'submit' || s.state === 'none' || s.state === 'draft';
          return (
            <div key={s.student_id} style={{ borderTop: '1px solid var(--vkui--color_background_secondary)', padding: '10px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text weight="2">{s.name}</Text>
                {/* «На доработку» — янтарный чип как в карточке ученика */}
                {s.state === 'change' ? (
                  <span style={{
                    minWidth: 28, height: 28, borderRadius: 7,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    paddingInline: 8, fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap',
                    background: 'var(--vkui--color_background_warning)',
                    border: '1px solid var(--vkui--color_icon_warning)',
                    color: 'var(--vkui--color_text_primary)',
                  }}>
                    {STATE_LABEL[s.state] || s.state}
                  </span>
                ) : (
                  <Counter
                    mode="primary"
                    appearance={s.state === 'accept' ? 'accent-green'
                      : s.state === 'reject' ? 'accent-red' : undefined}
                  >
                    {STATE_LABEL[s.state] || s.state}
                  </Counter>
                )}
              </div>
              {s.answer && (
                <Text style={{
                  color: 'var(--vkui--color_text_primary)',
                  fontWeight: 600,
                  display: 'block', marginTop: 4, whiteSpace: 'pre-wrap',
                }}>
                  Ответ: {s.answer}
                </Text>
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
              {!canReview && s.mark && (
                <Caption style={{
                  color: 'var(--vkui--color_text_secondary)',
                  display: 'block', marginTop: 4,
                }}>
                  Оценка: {s.mark}
                </Caption>
              )}
              {/* История сдачи из mail-трекинга (ru.po лейблы): На проверке
                  18.09 → На доработке 19.09 → … Хронология внизу строки. */}
              {s.history && s.history.length > 0 && (
                <Caption style={{
                  color: 'var(--vkui--color_text_secondary)',
                  display: 'block', marginTop: 6,
                }}>
                  {s.history.map((ev, i) => (
                    <span key={i} style={{ display: 'block' }}>
                      {ev.label} {ev.date}
                    </span>
                  ))}
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
                  {/* Оценка — кнопка журнала (цикл — → 5 → 4 → 3 → 2 → —),
                      не текстовое поле. Ставится только при «Принять».
                      Кнопка оценки в одном ряду с кнопками, прижата вправо. */}
                  <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
                    <Button
                      size="s"
                      appearance="positive"
                      loading={busyId === subId}
                      onClick={() => review(s, 'accept')}
                    >
                      Принять
                    </Button>
                    {/* «На доработку» только у сдавших: без ответа нечего
                        возвращать; несдавшему создаётся сдача state=accept. */}
                    {s.state === 'submit' && (
                      <Button
                        size="s"
                        mode="outline"
                        appearance="negative"
                        disabled={busyId === subId}
                        onClick={() => review(s, 'change')}
                      >
                        На доработку
                      </Button>
                    )}
                    <span style={{ marginLeft: 'auto' }}>
                      <JournalButton
                        kind="grade"
                        value={marks[subId] ?? null}
                        onCycle={next => setMarks(prev => ({ ...prev, [subId]: next }))}
                        title="Оценка за домашнее задание"
                      />
                    </span>
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
