import React from 'react';
import { Panel, Spinner, Div, Button, Text, Card as VkCard, Counter, Caption } from '@vkontakte/vkui';
import { useAppStore } from '@/shared/lib/store';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { today } from '@/shared/lib/date';
import type { DashboardInfoResponse } from '@/shared/lib/types';
import {
  Greeting,
  TodayLessons,
  GradesToday,
  AdminStatStrip,
  AdminAlerts,
} from './components/feed';
import { HomeworkCardList as HomeworkList } from '@/shared/components/HomeworkCardList';

interface DashboardPageProps {
  id: string;
  onOpenLesson: (sheetId: number) => void;
  onOpenTimetable: () => void;
  onOpenGrades: () => void;
  onOpenHomework: () => void;
  onOpenProfile: () => void;
}

/** Табло ДЗ учителя/админа: только счётчики, клик уводит на вкладку
 *  «Задания» (там списки, проверка и правка). */
export const HwSummaryCard: React.FC<{
  summary: { to_review: number; active: number };
  onOpenHomework: () => void;
}> = ({ summary, onOpenHomework }) => (
  <div style={{ margin: '0 8px 8px' }}>
    <VkCard mode="shadow" style={{ overflow: 'hidden' }} onClick={onOpenHomework}>
      <div style={{
        padding: '12px 16px', display: 'flex',
        justifyContent: 'space-between', alignItems: 'center',
      }}>
        <Text weight="2">Домашние задания</Text>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {summary.to_review > 0 && (
            <Counter mode="primary" appearance="accent-red">
              {`${summary.to_review} к проверке`}
            </Counter>
          )}
          <Counter mode="primary">{`${summary.active} активных`}</Counter>
        </div>
      </div>
      <Caption
        style={{
          color: 'var(--vkui--color_text_secondary)',
          display: 'block', padding: '0 16px 12px',
        }}
      >
        Открыть задания
      </Caption>
    </VkCard>
  </div>
);

export const DashboardPage: React.FC<DashboardPageProps> = ({
  id, onOpenLesson, onOpenTimetable, onOpenGrades, onOpenHomework, onOpenProfile,
}) => {
  const userInfo = useAppStore(s => s.userInfo);
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
        `/rost_max/api/dashboard_info?date=${feedDate}`);
      setData(res);
    } catch {
      addToast('Не удалось загрузить главную', 'error');
    } finally {
      setLoading(false);
    }
  }, [feedDate, addToast]);

  React.useEffect(() => { load(); }, [load]);

  const submitHomework = async (
    assignmentId: number,
    answer: string,
    files: { filename: string; mimetype: string; b64: string }[],
  ): Promise<string | null> => {
    try {
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/submit`,
        { answer, files });
      if (res.error) {
        addToast(res.error, 'error');
        return res.error;
      }
      addToast('Домашнее задание сдано', 'success');
      return null;
    } catch {
      addToast('Не удалось сдать задание', 'error');
      return 'error';
    }
  };

  const userName = userInfo?.user_name ?? '';
  const isAdmin = Boolean(data?.is_admin);
  const isTeacher = Boolean(data?.is_teacher) && !isAdmin;
  const isStudentOrParent = !isAdmin && !isTeacher;

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
            short={isStudentOrParent}
            onOpenProfile={onOpenProfile}
          />

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
            grouped={isAdmin}
          />

          {/* Ученик: оценки за сегодня + ДЗ */}
          {isStudentOrParent && data.grades_today && (
            <GradesToday grades={data.grades_today} onOpenGrades={onOpenGrades} />
          )}
          {isStudentOrParent && data.homework && (
            <HomeworkList
              items={data.homework.filter(h => h.state !== 'submit' && h.state !== 'accept')}
              max={3}
              title={<Text weight="2">Домашние задания</Text>}
              afterTitle={
                <span
                  style={{
                    color: 'var(--vkui--color_text_accent)',
                    fontWeight: 500, cursor: 'pointer', fontSize: 13,
                  }}
                  onClick={onOpenHomework}
                >
                  Все задания →
                </span>
              }
              canSubmit={Boolean(data.is_student)}
              onSubmit={submitHomework}
              onUpdated={load}
            />
          )}

          {/* Учитель/админ: табло ДЗ — только счётчики, вся логика
              (списки, проверка, правка) на вкладке «Задания». */}
          {(isTeacher || isAdmin) && data.hw_summary && (
            <HwSummaryCard
              summary={data.hw_summary}
              onOpenHomework={onOpenHomework}
            />
          )}
        </>
      )}
    </Panel>
  );
};
