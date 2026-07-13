import React from 'react';
import { createBrowserRouter, RouterProvider, Outlet, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from './store';
import { today } from '../shared/lib';
import { Layout } from '../shared/ui/Layout';
import { TabBar } from '../widgets/tab-bar';
import { LoginPageScreen } from '../pages/LoginPage';
import { DashboardPageScreen } from '../pages/DashboardPage';
import { TimetablePageScreen } from '../pages/TimetablePage';
import { LessonJournalPageScreen } from '../pages/LessonJournalPage';
import { ModulesPageScreen } from '../pages/ModulesPage';

// Корневой layout под префиксом /rost_max: грузит профиль при старте и
// рендерит дочерние роуты через <Outlet />.
const RootLayout: React.FC = () => {
  const location = useLocation();
  const loadUserInfo = useAppStore(s => s.loadUserInfo);

  React.useEffect(() => {
    if (location.pathname !== '/rost_max/login') {
      loadUserInfo();
    }
  }, [loadUserInfo]);

  return <Outlet />;
};

// Макет для экранов с таб-баром (инкапсулирует загрузку профиля + TabBar)
const TabbedLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const userLoading = useAppStore(s => s.userLoading);

  if (userLoading) {
    return (
      <Layout>
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
          Загрузка профиля...
        </div>
      </Layout>
    );
  }

  const isDashboard = location.pathname === '/rost_max/dashboard';
  const isModules = location.pathname === '/rost_max/modules';
  const currentTab = isDashboard ? 'dashboard' : isModules ? 'modules' : 'timetable';

  return (
    <Layout>
      <Outlet />
      <TabBar
        currentTab={currentTab}
        onTabChange={(tab: string) => navigate(`/rost_max/${tab}`)}
      />
    </Layout>
  );
};

// После логина подгружаем профиль ДО перехода на дашборд. loadUserInfo — из
// стора напрямую (вне React), навигация — через router.navigate (метод
// объекта router, без useNavigate в модуле). Сбрасываем дату и фильтр
// преподавателя на дефолт — в новой сессии всегда today + без фильтра,
// внутри сессии выбор хранится в sessionStorage.
const handleLoginSuccess = async (router: ReturnType<typeof createBrowserRouter>) => {
  await useAppStore.getState().loadUserInfo();
  const store = useAppStore.getState();
  store.setGlobalDate(today());
  store.setFilters({ selectedFaculty: null });
  router.navigate('/rost_max/dashboard');
};

const router = createBrowserRouter([
  {
    path: '/rost_max',
    element: <RootLayout />,
    children: [
      // Корень /rost_max -> расписание (явный index, без catch-all '*')
      { index: true, element: <Navigate to="timetable" replace /> },
      { path: 'login', element: <LoginPageScreen onSuccess={() => handleLoginSuccess(router)} /> },
      { path: 'lesson/:id', element: <LessonJournalPageScreen /> },
      {
        element: <TabbedLayout />,
        children: [
          { path: 'dashboard', element: <DashboardPageScreen onNavigate={(to) => router.navigate(to)} /> },
          { path: 'timetable', element: <TimetablePageScreen onOpenLesson={(id) => router.navigate(`/rost_max/lesson/${id}`)} /> },
          { path: 'modules', element: <ModulesPageScreen /> },
        ],
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
