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
import { Icon28HomeOutline, Icon28CalendarOutline, Icon28BookSpreadOutline } from '@vkontakte/icons';
import { LoginPage } from '@/pages/auth/LoginPage';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { TimetablePage } from '@/pages/timetable/TimetablePage';
import { SubjectsPage } from '@/pages/subjects/SubjectsPage';
import { SubjectGradesPage } from '@/pages/subjects/SubjectGradesPage';
import { LessonJournalPage } from '@/pages/lesson-journal/LessonJournalPage';
import { ToastContainer } from '@/shared/components/Toast';
import { useAppStore } from '@/shared/lib/store';

type TabId = 'dashboard' | 'timetable' | 'subjects';

export default function App() {
  const authSuccess = useAppStore(s => s.authSuccess);
  const userInfo = useAppStore(s => s.userInfo);
  const [activeView, setActiveView] = React.useState<'login' | 'main' | 'lesson-journal'>('login');
  const [activeTab, setActiveTab] = React.useState<TabId>('dashboard');

  // Состояние для вложенной навигации внутри таба "Расписание"
  const [timetableHistory, setTimetableHistory] = React.useState<string[]>(['timetable-panel']);
  const [selectedLessonId, setSelectedLessonId] = React.useState<number | null>(null);

  // Вложенная навигация внутри таба "Успеваемость"
  const [subjectsHistory, setSubjectsHistory] = React.useState<string[]>(['subjects-panel']);
  const [selectedSubject, setSelectedSubject] = React.useState<{ id: number; name: string } | null>(null);

  const activeTimetablePanel = timetableHistory[timetableHistory.length - 1];
  const activeSubjectsPanel = subjectsHistory[subjectsHistory.length - 1];

  // Таб «Оценки» виден только ученику и родителю
  const isStudentOrParent = Boolean(
    userInfo && (userInfo.is_student || userInfo.is_parent) && !userInfo.is_admin && !userInfo.is_teacher
  );

  const handleOpenSubject = (subjectId: number, subjectName: string) => {
    setSelectedSubject({ id: subjectId, name: subjectName });
    setSubjectsHistory(h => [...h, 'subject-grades-panel']);
  };

  const handleSubjectsBack = () => {
    if (subjectsHistory.length > 1) {
      setSubjectsHistory(h => h.slice(0, -1));
      setSelectedSubject(null);
    }
  };

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

  // Намеренно глушим системный swipe-back VKUI: переход назад только по
  // кнопке «Назад» (системный жест в MAX конфликтует с закрытием приложения)
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
                {isStudentOrParent && (
                  <TabbarItem
                    label="Оценки"
                    selected={activeTab === 'subjects'}
                    onClick={() => setActiveTab('subjects')}
                  >
                    <Icon28BookSpreadOutline />
                  </TabbarItem>
                )}
              </Tabbar>
            }
          >
            {/* Дочерние View внутри Epic. ID каждого View обязан совпадать с activeStory */}
            <View id="dashboard" activePanel="dashboard-panel">
              <DashboardPage id="dashboard-panel" />
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

            <View
              id="subjects"
              activePanel={activeSubjectsPanel}
              history={subjectsHistory}
              onSwipeBack={handleSubjectsBack}
            >
              <SubjectsPage id="subjects-panel" onOpenSubject={handleOpenSubject} />
              <SubjectGradesPage
                id="subject-grades-panel"
                subjectId={selectedSubject?.id ?? 0}
                subjectName={selectedSubject?.name ?? ''}
                onBack={handleSubjectsBack}
              />
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