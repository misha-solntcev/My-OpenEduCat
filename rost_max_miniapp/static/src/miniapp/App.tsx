import React from 'react';
import { LoginPage } from './pages/LoginPage';
import { TimetablePage } from './pages/TimetablePage';
import { LessonJournalPage } from './pages/LessonJournalPage';
import { Layout } from './Layout';

export default function App() {
  const pathname = window.location.pathname;
  
  // Роутинг по URL
  const lessonMatch = pathname.match(/\/rost_max\/lesson\/(\d+)/);
  const lessonId = lessonMatch ? parseInt(lessonMatch[1]) : null;
  const isLogin = pathname === '/rost_max/login';
  const isTimetable = pathname.includes('/timetable') || (!lessonId && !isLogin && pathname !== '/rost_max/dashboard');

  if (isLogin) {
    return <LoginPage />;
  }

  // Если открыт журнал урока - показываем его
  if (lessonId) {
    return <LessonJournalPage lessonId={lessonId} lessonTitle="Журнал оценок" onBack={() => { window.location.href = '/rost_max/timetable'; }} />;
  }

  // Иначе обычная навигация через таб-бар
  const [currentTab, setCurrentTab] = React.useState('timetable');

  return (
    <Layout 
      title={currentTab === 'timetable' ? 'Расписание' : 'Сервисы РОСТ'} 
      currentTab={currentTab} 
      onTabChange={setCurrentTab}
    >
      {currentTab === 'timetable' && <TimetablePage />}
    </Layout>
  );
}