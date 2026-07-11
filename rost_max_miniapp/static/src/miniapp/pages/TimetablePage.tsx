import { TimetablePage } from '../features/timetable';

export const TimetablePageScreen: React.FC<{ onOpenLesson: (id: number) => void }> = ({ onOpenLesson }) => (
  <TimetablePage onOpenLesson={onOpenLesson} />
);
