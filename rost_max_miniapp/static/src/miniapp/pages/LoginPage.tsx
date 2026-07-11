import { LoginPage } from '../features/login';

export const LoginPageScreen: React.FC<{ onSuccess: () => void }> = ({ onSuccess }) => (
  <LoginPage onSuccess={onSuccess} />
);
