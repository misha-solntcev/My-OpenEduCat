import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LessonJournalPage as LessonJournalPageView } from './LessonJournalPage';

// Обёртка для роутера: достаёт :id из пути и даёт onBack.
// Сам LessonJournalPage остаётся чистым презентационным компонентом.
export const LessonJournalPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  return (
    <LessonJournalPageView
      lessonId={id ? Number(id) : 0}
      onBack={() => navigate('/rost_max/timetable')}
    />
  );
};
