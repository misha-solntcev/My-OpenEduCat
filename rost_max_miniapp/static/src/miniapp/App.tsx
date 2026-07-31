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
import { LoginPage } from '@/pages/auth/LoginPage';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { TimetablePage } from '@/pages/timetable/TimetablePage';
import { ModulesPage } from '@/pages/modules/ModulesPage';
import { LessonJournalPage } from '@/pages/lesson-journal/LessonJournalPage';
import { ToastContainer } from '@/shared/components/Toast';
import { useAppStore } from '@/shared/lib/store';

type TabId = 'dashboard' | 'timetable' | 'modules';

export default function App() {
  const authSuccess = useAppStore(s => s.authSuccess);
  const userInfo = useAppStore(s => s.userInfo);
  const [activeView, setActiveView] = React.useState<'login' | 'main' | 'lesson-journal'>('login');
  const [activeTab, setActiveTab] = React.useState<TabId>('dashboard');

  // Состояние для вложенной навигации внутри таба "Расписание"
  const [timetableHistory, setTimetableHistory] = React.useState<string[]>(['timetable-panel']);
  const [selectedLessonId, setSelectedLessonId] = React.useState<number | null>(null);

  const activeTimetablePanel = timetableHistory[timetableHistory.length - 1];

  const handleOpenLesson = (lessonId: number) => {
    setSelectedLessonId(lessonId);
    setActiveView('lesson-journal');
  };

  const handleTimetableBack = () => {
    if (timetableHistory.length > 1) {
      setTimetableHistory(prev => prev.slice(0, -1));
      setSelectedLessonId(null);
    } else {
      // Возвращаемся к табам
      setActiveView('main');
      setActiveTab('timetable');
      setSelectedLessonId(null);
    }
  };

  const handleSwipeBackStart = (_activePanel: string) => {
    return undefined;
  };

  // Управляем глобальным переключением экранов
  React.useEffect(() => {
    if (authSuccess || userInfo) {
      if (activeView === 'login') {
        setActiveView('main');
      }
    } else {
      setActiveView('login');
    }
  }, [authSuccess, userInfo]);

  return (
    <SplitLayout>
      <SplitCol autoSpaced>
        {/* Root переключает глобальные независимые экраны */}
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

            <View
              id="timetable"
              activePanel={activeTimetablePanel}
              history={timetableHistory}
              onSwipeBack={handleTimetableBack}
              onSwipeBackStart={handleSwipeBackStart}
            >
              <TimetablePage id="timetable-panel" onOpenLesson={handleOpenLesson} />
            </View>

            <View id="modules" activePanel="modules-panel">
              <ModulesPage id="modules-panel" />
            </View>
          </Epic>

          {/* 3. Журнал урока — отдельный View на уровне Root (вне Epic), 
              чтобы модалки/шторки не перекрывались Tabbar'ом */}
          <View id="lesson-journal" activePanel="lesson-journal-panel">
            <LessonJournalPage 
              id="lesson-journal-panel" 
              lessonId={selectedLessonId} 
              onBack={handleTimetableBack} 
            />
          </View>

        </Root>
        <ToastContainer />
      </SplitCol>
    </SplitLayout>
  );
}