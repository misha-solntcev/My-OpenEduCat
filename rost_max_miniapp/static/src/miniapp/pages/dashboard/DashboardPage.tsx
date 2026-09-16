import React from 'react';
import { Panel, Spinner, Div, Button, Text } from '@vkontakte/vkui';
import { useAppStore } from '@/shared/lib/store';
import { apiGet, apiPost } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { today } from '@/shared/lib/date';
import type { DashboardInfoResponse, HomeworkSubmissionsResponse } from '@/shared/lib/types';
import {
  Greeting,
  TodayLessons,
  GradesToday,
  JournalsToFill,
  MyHomework,
  SubmissionReviewCard,
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

export const DashboardPage: React.FC<DashboardPageProps> = ({
  id, onOpenLesson, onOpenTimetable, onOpenGrades, onOpenHomework, onOpenProfile,
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
              items={data.homework}
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

          {/* Учитель: журналы к заполнению + задано моими уроками */}
          {isTeacher && data.journals_to_fill && (
            <JournalsToFill items={data.journals_to_fill} onOpenJournal={onOpenLesson} />
          )}
          {isTeacher && reviewId != null && (
            reviewData ? (
              <SubmissionReviewCard
                submission={reviewData}
                onClose={() => { setReviewId(null); setReviewData(null); }}
                onReview={reviewSubmission}
                onUpdated={load}
              />
            ) : (
              // Ответ /submissions ещё грузится — карточке нельзя рендериться
              // с null (внутри деструктуризация assignment/students).
              <Div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}>
                <Spinner size="m" />
              </Div>
            )
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
        </>
      )}
    </Panel>
  );
};
