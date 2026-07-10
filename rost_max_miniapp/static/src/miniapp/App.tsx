import React from 'react';
import { LoginPage } from './pages/LoginPage';
import { TimetablePage } from './pages/TimetablePage';
import { LessonJournalPage } from './pages/LessonJournalPage';
import { DashboardPage } from './pages/DashboardPage';
import { Layout } from './Layout';

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
      title={currentTab === 'timetable' ? 'Расписание' : 'Сервисы РОСТ'}
      currentTab={currentTab}
      onTabChange={handleTabChange}
    >
      {currentTab === 'dashboard' && <DashboardPage onNavigate={navigate} />}
      {currentTab === 'timetable' && <TimetablePage onOpenLesson={(id) => navigate(`/rost_max/lesson/${id}`)} />}
      {currentTab === 'modules' && (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Раздел «Модули» в разработке
        </div>
      )}
    </Layout>
  );
}
