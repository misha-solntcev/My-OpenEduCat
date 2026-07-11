import { DashboardPage } from '../features/dashboard';

export const DashboardPageScreen: React.FC<{ onNavigate: (path: string) => void }> = ({ onNavigate }) => (
  <DashboardPage onNavigate={onNavigate} />
);
