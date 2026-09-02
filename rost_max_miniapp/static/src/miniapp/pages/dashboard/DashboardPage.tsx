import React from 'react';
import { Panel, PanelHeader, Spinner, Div, Button } from '@vkontakte/vkui';
import { useAppStore, selectGlobalDate } from '@/shared/lib/store';
import { apiGet } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import type { DashboardInfoResponse } from '@/shared/lib/types';
import {
  Greeting,
  TodayLessons,
  GradesToday,
  HomeworkList,
  JournalsToFill,
  MyHomework,
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
  const globalDate = useAppStore(selectGlobalDate);
  const addToast = useToast();

  const [data, setData] = React.useState<DashboardInfoResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiGet<DashboardInfoResponse>(
        `/rost_max/api/dashboard_info?date=${globalDate}`);
      setData(res);
    } catch {
      addToast('Не удалось загрузить главную', 'error');
    } finally {
      setLoading(false);
    }
  }, [globalDate, addToast]);

  React.useEffect(() => { load(); }, [load]);

  const userName = userInfo?.user_name ?? '';
  const isAdmin = Boolean(data?.is_admin);
  const isTeacher = Boolean(data?.is_teacher) && !isAdmin;
  const isStudentOrParent = !isAdmin && !isTeacher;

  return (
    <Panel id={id}>
      <PanelHeader>Главная</PanelHeader>

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
          <Greeting name={userName} date={data.date} short={isStudentOrParent} />

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

          {/* Лента уроков дня */}
          <TodayLessons
            lessons={data.lessons}
            onOpenJournal={isAdmin || isTeacher ? onOpenLesson : undefined}
            onOpenTimetable={onOpenTimetable}
            showBatch={isAdmin || isTeacher}
          />

          {/* Ученик: оценки за сегодня + ДЗ */}
          {isStudentOrParent && data.grades_today && (
            <GradesToday grades={data.grades_today} onOpenGrades={onOpenGrades} />
          )}
          {isStudentOrParent && data.homework && (
            <HomeworkList items={data.homework} />
          )}

          {/* Учитель: журналы к заполнению + задано моими уроками */}
          {isTeacher && data.journals_to_fill && (
            <JournalsToFill items={data.journals_to_fill} onOpenJournal={onOpenLesson} />
          )}
          {isTeacher && data.my_homework && (
            <MyHomework items={data.my_homework} />
          )}

          {/* Выход — реальная навигация, чтобы Odoo закрыл сессию серверно */}
          <Div style={{ paddingTop: 8, paddingBottom: 24 }}>
            <Button
              mode="outline"
              appearance="negative"
              stretched
              onClick={() => { window.location.href = '/rost_max/logout'; }}
            >
              Выйти
            </Button>
          </Div>
        </>
      )}
    </Panel>
  );
};
