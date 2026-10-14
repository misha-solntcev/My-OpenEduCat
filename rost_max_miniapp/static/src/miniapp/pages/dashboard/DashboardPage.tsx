import React from 'react';
import { Panel, Spinner, Div, Button, Text, Card as VkCard, Counter, SegmentedControl } from '@vkontakte/vkui';
import { useAppStore, childQuery, scopeQuery } from '@/shared/lib/store';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { today } from '@/shared/lib/date';
import type { DashboardInfoResponse, ChildInfo } from '@/shared/lib/types';
import {
  Greeting,
  TodayLessons,
  GradesToday,
  AdminStatStrip,
  AdminAlerts,
} from './components/feed';

interface DashboardPageProps {
  id: string;
  onOpenLesson: (sheetId: number) => void;
  onOpenTimetable: () => void;
  onOpenGrades: () => void;
  onOpenHomework: () => void;
  onOpenProfile: () => void;
}

/* Строка «точка + подпись + счётчик-плашка» — вариант Б мокапа
 * (design/student-hw-card-variants.html): язык групп вкладки «Задания».
 * Нулевые строки не рендерим. */
const HwSummaryRow: React.FC<{
  dot: string;
  label: string;
  count: number;
  counterAppearance: 'accent' | 'accent-red' | 'accent-green';
}> = ({ dot, label, count, counterAppearance }) => (
  <div style={{
    display: 'flex', alignItems: 'center',
    padding: '9px 16px', borderTop: '1px solid var(--vkui--color_separator_primary)',
  }}>
    <span style={{
      width: 8, height: 8, borderRadius: '50%', marginRight: 10,
      flexShrink: 0, background: dot,
    }} />
    <span style={{ fontSize: 14, flex: 1 }}>{label}</span>
    <Counter mode="primary" appearance={counterAppearance}>{count}</Counter>
    <span style={{
      marginLeft: 10, color: 'var(--vkui--color_icon_tertiary)', fontSize: 14,
    }}>›</span>
  </div>
);

/** Табло ДЗ ученика: строки статусов (Вариант Б), клик — вкладка «Задания».
 *  Новые без сдачи; На доработке — вернулось от учителя; На проверке —
 *  сдано; Проверено — принято (за всё время); Просрочено — срок прошёл,
 *  сдачи нет (отдельной строкой, из «Новых» исключается).
 *  Окна по дате нет (2026-09-19): лента фильтруется статусом, не датой,
 *  поэтому счётчики главной всегда равны сегментам вкладки «Задания». */
export const StudentHwCard: React.FC<{
  items: { state: string; overdue: boolean }[];
  onOpenHomework: () => void;
}> = ({ items, onOpenHomework }) => {
  const fresh = items.filter(
    h => (h.state === 'none' || h.state === 'draft') && !h.overdue).length;
  const change = items.filter(h => h.state === 'change' || h.state === 'reject').length;
  const submitted = items.filter(h => h.state === 'submit').length;
  const checked = items.filter(h => h.state === 'accept').length;
  const overdue = items.filter(
    h => h.overdue && h.state !== 'submit' && h.state !== 'accept').length;
  // Просрочено — первое: горящее всегда сверху
  const rows = [
    overdue > 0 && { dot: 'var(--vkui--color_icon_negative)', label: 'Просрочено',
      count: overdue, appearance: 'accent-red' as const },
    fresh > 0 && { dot: 'var(--vkui--color_background_accent)', label: 'Новые',
      count: fresh, appearance: 'accent' as const },
    change > 0 && { dot: 'var(--vkui--color_icon_negative)', label: 'На доработке',
      count: change, appearance: 'accent-red' as const },
    submitted > 0 && { dot: 'var(--vkui--color_icon_warning)', label: 'На проверке',
      count: submitted, appearance: 'accent' as const },
    checked > 0 && { dot: 'var(--vkui--color_icon_positive)', label: 'Проверено',
      count: checked, appearance: 'accent-green' as const },
  ].filter(Boolean) as { dot: string; label: string; count: number;
    counterAppearance: 'accent' | 'accent-red' | 'accent-green' }[];
  if (rows.length === 0) return null;
  return (
    <div style={{ margin: '0 8px 8px' }}>
      <VkCard mode="shadow" style={{ overflow: 'hidden' }} onClick={onOpenHomework}>
        <div style={{ padding: '12px 16px 10px' }}>
          <Text weight="2">Домашние задания</Text>
        </div>
        {rows.map(r => <HwSummaryRow key={r.label} {...r} />)}
      </VkCard>
    </div>
  );
};

/** Табло ДЗ учителя/админа: строки статусов, как у ученика (Вариант Б),
 *  сегменты вкладки «Задания»: Проверить / Выдано / Проверено.
 *  Клик — вкладка. Нулевые строки не рендерим. */
export const TeacherHwCard: React.FC<{
  summary: { to_review: number; issued: number; checked: number };
  onOpenHomework: () => void;
}> = ({ summary, onOpenHomework }) => {
  const rows = [
    summary.to_review > 0 && {
      dot: 'var(--vkui--color_icon_negative)', label: 'Проверить',
      count: summary.to_review, counterAppearance: 'accent-red' as const,
    },
    summary.issued > 0 && {
      dot: 'var(--vkui--color_background_accent)', label: 'Выдано',
      count: summary.issued, counterAppearance: 'accent' as const,
    },
    summary.checked > 0 && {
      dot: 'var(--vkui--color_icon_positive)', label: 'Проверено',
      count: summary.checked, counterAppearance: 'accent-green' as const,
    },
  ].filter(Boolean) as { dot: string; label: string; count: number;
    counterAppearance: 'accent' | 'accent-red' | 'accent-green' }[];
  if (rows.length === 0) return null;
  return (
    <div style={{ margin: '0 8px 8px' }}>
      <VkCard mode="shadow" style={{ overflow: 'hidden' }} onClick={onOpenHomework}>
        <div style={{ padding: '12px 16px 10px' }}>
          <Text weight="2">Домашние задания</Text>
        </div>
        {rows.map(r => <HwSummaryRow key={r.label} {...r} />)}
      </VkCard>
    </div>
  );
};

/** Переключатель режимов главной (сегмент, Вариант C).
 *  Опции по АККАУНТУ: учитель — «Мои уроки», админ — «Мои уроки» (если
 *  сам преподаёт) + «Школа» (обзор завуча), потом дети. Родитель: только
 *  дети (2+; с одним ребёнком свитч не рисуем — данные сразу за него).
 *  Значения: 'mine' | 'school' | String(childId). */
export const ChildSwitcher: React.FC<{
  children: ChildInfo[];
  isTeacherAccount: boolean;
  isAdminAccount: boolean;
  selected: string;
  onChange: (v: string) => void;
}> = ({ children: kids, isTeacherAccount, isAdminAccount, selected, onChange }) => {
  const options = [
    ...(isTeacherAccount ? [{ label: 'Мои уроки', value: 'mine' }] : []),
    ...(isAdminAccount ? [{ label: 'Школа', value: 'school' }] : []),
    ...kids.map(k => ({ label: `${k.name.split(' ')[1] ?? k.name} · ${k.batch}`, value: String(k.id) })),
  ];
  // Одна опция — переключать нечего (учитель без детей, админ без детей).
  if (options.length < 2) return null;
  return (
    <div style={{ paddingInline: 16, paddingBottom: 10 }}>
      <SegmentedControl value={selected} options={options} onChange={onChange} />
    </div>
  );
};

export const DashboardPage: React.FC<DashboardPageProps> = ({
  id, onOpenLesson, onOpenTimetable, onOpenGrades, onOpenHomework, onOpenProfile,
}) => {
  const userInfo = useAppStore(s => s.userInfo);
  const selectedChildId = useAppStore(s => s.selectedChildId);
  const setChildId = useAppStore(s => s.setChildId);
  const schoolMode = useAppStore(s => s.schoolMode);
  const setSchoolMode = useAppStore(s => s.setSchoolMode);
  const addToast = useToast();

  const [data, setData] = React.useState<DashboardInfoResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  // Главная всегда про сегодняшний день (Europe/Moscow) — независимо от
  // навигации по расписанию. Дата фиксируется на монтирование.
  const [feedDate] = React.useState(today);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiGet<DashboardInfoResponse>(
        `/rost_max/api/dashboard_info?date=${feedDate}${scopeQuery()}${childQuery()}`);
      setData(res);
    } catch {
      addToast('Не удалось загрузить главную', 'error');
    } finally {
      setLoading(false);
    }
  }, [feedDate, selectedChildId, schoolMode, addToast]);

  React.useEffect(() => { load(); }, [load]);

  const userName = userInfo?.user_name ?? '';
  const isAdmin = Boolean(data?.is_admin);
  const isTeacher = Boolean(data?.is_teacher) && !isAdmin;
  const isStudentOrParent = !isAdmin && !isTeacher;

  // Роль АККАУНТА (не режима): приветствие учителя остаётся
  // «Здравствуйте, Надежда Николаевна» и в режиме ребёнка.
  const isStaffAccount = Boolean(userInfo?.is_teacher || userInfo?.is_admin);
  const kids = userInfo?.children ?? [];
  const child = kids.find(k => k.id === selectedChildId) ?? null;
  const switchValue = child ? String(child.id) : schoolMode ? 'school' : 'mine';
  // Имя ребёнка для заголовка ленты: имя из ФИО («Макаров Михаил
  // Игоревич» -> «Михаил», как в приветствии ученика).
  const childLabel = child ? (child.name.split(' ')[1] ?? child.name) : undefined;

  return (
    <Panel id={id}>
      {/* Корневой таб: без PanelHeader — активный таб виден в таббаре */}

      {loading && !data ? (
        <Div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spinner size="l" />
        </Div>
      ) : !data ? (
        <Div>
          <Button mode="outline" stretched onClick={load}>Повторить</Button>
        </Div>
      ) : (
        <>
          <Greeting
            name={userName}
            date={data.date}
            avatar={userInfo?.avatar}
            short={!isStaffAccount}
            onOpenProfile={onOpenProfile}
          />

          {/* Переключатель режимов (учитель/админ-родитель, родитель с 2+
              детьми). Рисуем по АККАУНТУ: флаги data в режиме ребёнка
              говорят «ученик», а свитч учителю всё равно нужен. */}
          {kids.length > 0 && (
            <ChildSwitcher
              children={kids}
              isTeacherAccount={Boolean(userInfo?.is_teacher)}
              isAdminAccount={Boolean(userInfo?.is_admin)}
              selected={switchValue}
              onChange={v => {
                if (v === 'mine') { setChildId(null); setSchoolMode(false); }
                else if (v === 'school') { setChildId(null); setSchoolMode(true); }
                else { setChildId(Number(v)); setSchoolMode(false); }
              }}
            />
          )}

          {/* Админ: полоса цифр + требует внимания */}
          {isAdmin && data.admin_stats && (
            <>
              <AdminStatStrip stats={data.admin_stats} />
              {data.alerts?.length ? (
                <AdminAlerts
                  unfilled={data.alerts[0].count}
                  morningPassed={data.alerts[0].morning_passed}
                />
              ) : (
                <AdminAlerts unfilled={0} morningPassed={0} />
              )}
            </>
          )}

          {/* Лента уроков дня; админу — слоты-аккордеоны (как в расписании) */}
          <TodayLessons
            lessons={data.lessons}
            onOpenJournal={isAdmin || isTeacher ? onOpenLesson : undefined}
            onOpenTimetable={onOpenTimetable}
            showBatch={isAdmin || isTeacher}
            grouped={isAdmin && !child}
            childLabel={childLabel}
          />

          {/* Ученик: оценки за сегодня */}
          {isStudentOrParent && data.grades_today && (
            <GradesToday grades={data.grades_today} onOpenGrades={onOpenGrades} />
          )}

          {/* ДЗ у всех ролей — информационное табло: только счётчики,
              вся работа со сдачей/проверкой на вкладке «Задания».
              Ученик: строки статусов (вариант Б мокапа); учитель/админ:
              компактная строка сегментов. */}
          {isStudentOrParent && data.homework && (
            <StudentHwCard
              items={data.homework}
              onOpenHomework={onOpenHomework}
            />
          )}
          {(isTeacher || isAdmin) && data.hw_summary && (
            <TeacherHwCard
              summary={data.hw_summary}
              onOpenHomework={onOpenHomework}
            />
          )}
        </>
      )}
    </Panel>
  );
};
