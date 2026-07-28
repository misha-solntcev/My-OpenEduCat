import React from 'react';
import {  
  Root,  
  SplitLayout,
  SplitCol,  
  View,
  Epic,
  Tabbar,
  TabbarItem,  
} from '@vkontakte/vkui';
import { Icon28HomeOutline, Icon28CalendarOutline, Icon28GridLayoutOutline } from '@vkontakte/icons';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { TimetablePage } from '@/pages/TimetablePage';
import { ModulesPage } from '@/pages/ModulesPage';
import { LessonJournalPage } from '@/pages/LessonJournalPage';
import { ToastContainer } from '@/components/Toast';
import { useAppStore } from '@/lib/store';

type TabId = 'dashboard' | 'timetable' | 'modules';

export default function App() {
  const authSuccess = useAppStore(s => s.authSuccess);
  const userInfo = useAppStore(s => s.userInfo);
  const [activeView, setActiveView] = React.useState<'login' | 'main'>('login');
  const [activeTab, setActiveTab] = React.useState<TabId>('dashboard');

  // Состояние для вложенной навигации внутри таба "Расписание"
  const [timetableHistory, setTimetableHistory] = React.useState<string[]>(['timetable-panel']);
  const [selectedLessonId, setSelectedLessonId] = React.useState<number | null>(null);

  const activeTimetablePanel = timetableHistory[timetableHistory.length - 1];

  const handleOpenLesson = (lessonId: number) => {
    setSelectedLessonId(lessonId);
    setTimetableHistory(prev => [...prev, 'lesson-journal-panel']);
  };

  const handleTimetableBack = () => {
    if (timetableHistory.length > 1) {
      setTimetableHistory(prev => prev.slice(0, -1));
      setSelectedLessonId(null);
    }
  };

  const handleSwipeBackStart = (_activePanel: string) => {
    // Блокируем свайп-бэк если есть несохраненные изменения в журнале
    // (можно расширить через колбэк из LessonJournalPage)
    return undefined;
  };

  // Управляем глобальным переключением экранов
  React.useEffect(() => {
    if (authSuccess || userInfo) {
      setActiveView('main');
    } else {
      setActiveView('login');
    }
  }, [authSuccess, userInfo]);

  return (
    <SplitLayout>
      <SplitCol autoSpaced>
        {/* Root переключает глобальные независимые экраны (Авторизация vs Внутренняя зона) */}
        <Root activeView={activeView}>
         
          {/* 1. Экран авторизации (без нижнего меню) */}
          <View id="login" activePanel="login-panel">
            <LoginPage id="login-panel" />
          </View>

          {/* 2. Экран приложения с таббаром внутри Epic */}
          <Epic
            id="main"
            activeStory={activeTab}
            tabbar={
              <Tabbar mode="horizontal">
                <TabbarItem
                  label="Главная"
                  selected={activeTab === 'dashboard'}
                  onClick={() => setActiveTab('dashboard')}
                >
                  <Icon28HomeOutline />
                </TabbarItem>
                <TabbarItem
                  label="Расписание"
                  selected={activeTab === 'timetable'}
                  onClick={() => setActiveTab('timetable')}
                >
                  <Icon28CalendarOutline />
                </TabbarItem>
                <TabbarItem
                  label="Модули"
                  selected={activeTab === 'modules'}
                  onClick={() => setActiveTab('modules')}
                >
                  <Icon28GridLayoutOutline />
                </TabbarItem>
              </Tabbar>
            }
          >
            {/* Дочерние View внутри Epic. ID каждого View обязан совпадать с activeStory */}
            <View id="dashboard" activePanel="dashboard-panel">
              <DashboardPage id="dashboard-panel" onNavigate={(panel) => setActiveTab(panel as TabId)} />
            </View>

            {/* Вложенный View внутри таба "Расписание" для поддержки навигации в журнал урока */}
            <View
              id="timetable"
              activePanel={activeTimetablePanel}
              history={timetableHistory}
              onSwipeBack={handleTimetableBack}
              onSwipeBackStart={handleSwipeBackStart}
            >
              <TimetablePage id="timetable-panel" onOpenLesson={handleOpenLesson} />
              <LessonJournalPage id="lesson-journal-panel" lessonId={selectedLessonId} onBack={handleTimetableBack} />
            </View>

            <View id="modules" activePanel="modules-panel">
              <ModulesPage id="modules-panel" />
            </View>
          </Epic>

        </Root>
        <ToastContainer />
      </SplitCol>
    </SplitLayout>
  );
}