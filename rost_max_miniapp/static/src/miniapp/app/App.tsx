import React from 'react';
import { BrowserRouter, useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from './store';
import { Layout } from '../shared/ui/Layout';
import { TabBar } from '../widgets/tab-bar';
import { LoginPageScreen } from '../pages/LoginPage';
import { DashboardPageScreen } from '../pages/DashboardPage';
import { TimetablePageScreen } from '../pages/TimetablePage';
import { LessonJournalPageScreen } from '../pages/LessonJournalPage';

const AppRoutes: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const userLoading = useAppStore(s => s.userLoading);
  const loadUserInfo = useAppStore(s => s.loadUserInfo);

  // Загрузка профиля и ролей при старте (вне экрана логина)
  React.useEffect(() => {
    if (location.pathname === '/rost_max/login') {
      return;
    }
    loadUserInfo();
  }, [location.pathname, loadUserInfo]);

  // Роутинг по URL
  const lessonMatch = location.pathname.match(/\/rost_max\/lesson\/(\d+)/);
  const lessonId = lessonMatch ? parseInt(lessonMatch[1]) : null;
  const isLogin = location.pathname === '/rost_max/login';
  const isDashboard = location.pathname === '/rost_max/dashboard';
  const isModules = location.pathname === '/rost_max/modules';
  const isLesson = lessonId !== null;
  // Любой неизвестный путь (в т.ч. корень) трактуем как расписание
  const isTimetable = !isLogin && !isDashboard && !isModules && !isLesson;

  if (isLogin) {
    return <LoginPageScreen onSuccess={() => navigate('/rost_max/dashboard')} />;
  }

  // Экран загрузки профиля (не на логине)
  if (userLoading) {
    return (
      <Layout>
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
          Загрузка профиля...
        </div>
      </Layout>
    );
  }

  // Если открыт журнал урока — показываем его (без таб-бара)
  if (isLesson) {
    return (
      <LessonJournalPageScreen
        lessonId={lessonId}
        lessonTitle="Журнал оценок"
        onBack={() => navigate('/rost_max/timetable')}
      />
    );
  }

  // Обычная навигация через таб-бар
  const currentTab = isTimetable ? 'timetable' : (isDashboard ? 'dashboard' : (isModules ? 'modules' : 'timetable'));

  return (
    <Layout>
      {currentTab === 'dashboard' && (
        <DashboardPageScreen onNavigate={navigate} />
      )}
      {currentTab === 'timetable' && (
        <TimetablePageScreen onOpenLesson={(id) => navigate(`/rost_max/lesson/${id}`)} />
      )}
      {currentTab === 'modules' && (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Раздел «Модули» в разработке
        </div>
      )}
      <TabBar
        currentTab={currentTab}
        onTabChange={(tab: string) => {
          if (tab === 'dashboard') navigate('/rost_max/dashboard');
          else if (tab === 'modules') navigate('/rost_max/modules');
          else navigate('/rost_max/timetable');
        }}
      />
    </Layout>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
