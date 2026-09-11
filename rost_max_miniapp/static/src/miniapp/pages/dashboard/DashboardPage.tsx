import React from 'react';
import { Panel, Spinner, Div, Button } from '@vkontakte/vkui';
import { useAppStore } from '@/shared/lib/store';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { today } from '@/shared/lib/date';
import type { DashboardInfoResponse, HomeworkSubmissionsResponse } from '@/shared/lib/types';
import {
  Greeting,
  TodayLessons,
  GradesToday,
  HomeworkList,
  JournalsToFill,
  MyHomework,
  SubmissionReviewCard,
  AdminStatStrip,
  AdminAlerts,
} from './components/feed';

interface DashboardPageProps {
  id: string;
  onOpenLesson: (sheetId: number) => void;
  onOpenTimetable: () => void;
  onOpenGrades: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  id, onOpenLesson, onOpenTimetable, onOpenGrades,
}) => {
  const userInfo = useAppStore(s => s.userInfo);
  const addToast = useToast();

  const [data, setData] = React.useState<DashboardInfoResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  // Учитель: открытый экран сдач по заданию (id = op.assignment.id)
  const [reviewId, setReviewId] = React.useState<number | null>(null);
  const [reviewData, setReviewData] = React.useState<HomeworkSubmissionsResponse | null>(null);

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

  const openReview = async (assignmentId: number) => {
    setReviewId(assignmentId);
    setReviewData(null);
    try {
      const res = await apiGet<HomeworkSubmissionsResponse>(
        `/rost_max/api/homework/${assignmentId}/submissions`);
      setReviewData(res);
    } catch {
      addToast('Не удалось загрузить сдачи', 'error');
      setReviewId(null);
    }
  };

  const reviewSubmission = async (
    subId: number,
    action: 'accept' | 'change',
    note: string,
  ): Promise<string | null> => {
    try {
      const res = await apiPost<{ success?: boolean; error?: string }>(
        `/rost_max/api/homework/submission/${subId}/review`,
        { action, teacher_note: note });
      if (res.error) {
        addToast(res.error, 'error');
        return res.error;
      }
      if (reviewId != null) await openReview(reviewId);
      addToast(action === 'accept' ? 'Принято' : 'Отправлено на доработку', 'success');
      return null;
    } catch {
      addToast('Не удалось сохранить проверку', 'error');
      return 'error';
    }
  };

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
          <Greeting name={userName} date={data.date} avatar={userInfo?.avatar} short={isStudentOrParent} />

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
              items={data.homework}
              canSubmit={Boolean(data.is_student)}
              onSubmit={submitHomework}
              onUpdated={load}
            />
          )}

          {/* Учитель: журналы к заполнению + задано моими уроками */}
          {isTeacher && data.journals_to_fill && (
            <JournalsToFill items={data.journals_to_fill} onOpenJournal={onOpenLesson} />
          )}
          {isTeacher && reviewId != null && (
            <SubmissionReviewCard
              submission={reviewData}
              onClose={() => { setReviewId(null); setReviewData(null); }}
              onReview={reviewSubmission}
              onUpdated={load}
            />
          )}
          {/* Учитель — свои ДЗ (аккордеон по классам); админ — вся школа
              (аккордеон по учителям; сервер кладёт их в тот же my_homework). */}
          {(isTeacher || isAdmin) && data.my_homework && (
            <MyHomework
              items={data.my_homework}
              groupBy={isAdmin ? 'faculty' : 'batch'}
              onOpen={openReview}
            />
          )}

          {/* Выход — реальная навигация, чтобы Odoo закрыл сессию серверно.
              Парящая кнопка по центру над таббаром: fixed + left/right 0 +
              margin auto. bottom = высота таббара (~56) + зазор. */}
          <div style={{
            position: 'fixed',
            left: 0, right: 0,
            bottom: 'calc(56px + var(--vkui--spacing_size_m))',
            display: 'flex',
            justifyContent: 'center',
            zIndex: 10,
            pointerEvents: 'none',
          }}>
            <Button
              mode="primary"
              appearance="negative"
              size="m"
              style={{ pointerEvents: 'auto' }}
              onClick={() => { window.location.href = '/rost_max/logout'; }}
            >
              Выйти
            </Button>
          </div>
        </>
      )}
    </Panel>
  );
};
