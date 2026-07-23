import React from 'react';
import { createBrowserRouter, RouterProvider, Outlet, Navigate, useNavigate, useLocation, useParams } from 'react-router-dom';
import { useAppStore } from '@/lib/store';
import { today } from '@/lib';
import { Layout } from '@/components/Layout';
import { TabBar } from '@/components/TabBar';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { TimetablePage } from '@/pages/TimetablePage';
import { LessonJournalPage } from '@/pages/LessonJournalPage';
import { ModulesPage } from '@/pages/ModulesPage';

// Обёртка для LessonJournalPage: достаёт lessonId из params и даёт onBack
const LessonJournalPageWrapper: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  return <LessonJournalPage lessonId={Number(id)} onBack={() => navigate('/rost_max/timetable')} />;
};
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
      { path: 'login', element: <LoginPage onSuccess={() => handleLoginSuccess(router)} /> },
      { path: 'lesson/:id', element: <LessonJournalPageWrapper /> },
      {
        element: <TabbedLayout />,
        children: [
          { path: 'dashboard', element: <DashboardPage onNavigate={(to) => router.navigate(to)} /> },
          { path: 'timetable', element: <TimetablePage onOpenLesson={(id) => router.navigate(`/rost_max/lesson/${id}`)} /> },
          { path: 'modules', element: <ModulesPage /> },
        ],
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
