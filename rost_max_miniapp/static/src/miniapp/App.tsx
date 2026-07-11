import React from 'react';
import { LoginPage } from './pages/LoginPage';
import { TimetablePage } from './pages/TimetablePage';
import { LessonJournalPage } from './pages/LessonJournalPage';
import { DashboardPage } from './pages/DashboardPage';
import { Layout } from './Layout';
import { apiGet } from './api';

interface UserInfo {
  user_name: string;
  is_admin: boolean;
  is_teacher: boolean;
  is_student: boolean;
}

// Лёгкий клиентский роутер на HTML5 History API (без сторонних зависимостей).
// pushState меняет URL без перезагрузки WebView; popstate ловит системную
// кнопку/жест «Назад» и возвращает на предыдущий экран внутри мини-приложения.
function useLocation() {
  const [path, setPath] = React.useState(window.location.pathname);
  React.useEffect(() => {
    const handlePopState = () => setPath(window.location.pathname);
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);
  const navigate = (to: string) => {
    window.history.pushState({}, '', to);
    setPath(to);
  };
  return [path, navigate] as const;
}

export default function App() {
  const [pathname, navigate] = useLocation();
  const [userInfo, setUserInfo] = React.useState<UserInfo | null>(null);
  const [userLoading, setUserLoading] = React.useState(true);
  const [globalDate, setGlobalDate] = React.useState(() => {
    try {
      const saved = sessionStorage.getItem('rost_max_timetable_filters');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.date === 'string' && parsed.date) return parsed.date;
      }
    } catch {}
    return new Date().toISOString().split('T')[0];
  });

  // Единая дата (Date Jumper): пишем и в state, и в sessionStorage, чтобы
  // дашборд и расписание были синхронизированы, а выбор переживал reload.
  const handleDateChange = (newDate: string) => {
    setGlobalDate(newDate);
    try {
      const saved = sessionStorage.getItem('rost_max_timetable_filters');
      const parsed = saved ? JSON.parse(saved) : {};
      sessionStorage.setItem('rost_max_timetable_filters', JSON.stringify({
        ...parsed,
        date: newDate,
      }));
    } catch {}
  };

  // Загрузка профиля и ролей при старте (вне экрана логина)
  React.useEffect(() => {
    if (pathname === '/rost_max/login') {
      setUserLoading(false);
      return;
    }
    apiGet<UserInfo>('/rost_max/api/user/info')
      .then(setUserInfo)
      .catch(() => {
        // 401/403 -> api.ts уже редиректит на логин; здесь просто гасим
        setUserInfo(null);
      })
      .finally(() => setUserLoading(false));
  }, [pathname]);

  // Роутинг по URL (точное сопоставление экранов, без ложных совпадений)
  const lessonMatch = pathname.match(/\/rost_max\/lesson\/(\d+)/);
  const lessonId = lessonMatch ? parseInt(lessonMatch[1]) : null;
  const isLogin = pathname === '/rost_max/login';
  const isDashboard = pathname === '/rost_max/dashboard';
  const isModules = pathname === '/rost_max/modules';
  const isLesson = lessonId !== null;
  // Любой неизвестный путь (в т.ч. корень) трактуем как расписание
  const isTimetable = !isLogin && !isDashboard && !isModules && !isLesson;

  if (isLogin) {
    return <LoginPage onSuccess={() => navigate('/rost_max/dashboard')} />;
  }

  // Экран загрузки профиля (не на логине)
  if (userLoading) {
    return (
      <Layout title="Загрузка...">
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
          Загрузка профиля...
        </div>
      </Layout>
    );
  }

  // Если открыт журнал урока — показываем его (без таб-бара)
  if (isLesson) {
    return (
      <LessonJournalPage
        lessonId={lessonId}
        lessonTitle="Журнал оценок"
        onBack={() => navigate('/rost_max/timetable')}
      />
    );
  }

  // Обычная навигация через таб-бар
  const currentTab = isDashboard ? 'dashboard' : (isModules ? 'modules' : 'timetable');
  const handleTabChange = (tab: string) => {
    if (tab === 'dashboard') navigate('/rost_max/dashboard');
    else if (tab === 'modules') navigate('/rost_max/modules');
    else navigate('/rost_max/timetable');
  };

  return (
    <Layout
      title={currentTab === 'timetable' ? 'Расписание' : currentTab === 'modules' ? 'Модули' : 'Главная'}
      currentTab={currentTab}
      onTabChange={handleTabChange}
    >
      {currentTab === 'dashboard' && (
        <DashboardPage
          onNavigate={navigate}
          isAdmin={userInfo?.is_admin ?? false}
          isTeacher={userInfo?.is_teacher ?? false}
          userName={userInfo?.user_name ?? ''}
          globalDate={globalDate}
          onDateChange={handleDateChange}
        />
      )}
      {currentTab === 'timetable' && (
        <TimetablePage
          onOpenLesson={(id) => navigate(`/rost_max/lesson/${id}`)}
          globalDate={globalDate}
          onDateChange={handleDateChange}
        />
      )}
      {currentTab === 'modules' && (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Раздел «Модули» в разработке
        </div>
      )}
    </Layout>
  );
}
