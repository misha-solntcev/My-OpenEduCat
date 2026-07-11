import { LessonJournalPage } from '../features/lesson-journal';

export const LessonJournalPageScreen: React.FC<{
  lessonId: number;
  lessonTitle: string;
  onBack: () => void;
}> = ({ lessonId, lessonTitle, onBack }) => (
  <LessonJournalPage lessonId={lessonId} lessonTitle={lessonTitle} onBack={onBack} />
);
