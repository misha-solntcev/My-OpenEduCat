import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LessonJournalPage } from '../features/lesson-journal';

export const LessonJournalPageScreen: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  return (
    <LessonJournalPage
      lessonId={id ? parseInt(id, 10) : 0}
      onBack={() => navigate('/rost_max/timetable')}
    />
  );
};
