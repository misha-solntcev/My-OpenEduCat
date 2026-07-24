import React from 'react';
import { Flex, Title, Text, Button, Input, Panel } from '@vkontakte/vkui';
import { apiPost } from '@/lib';

interface LoginResponse {
  success?: boolean;
  error?: string;
  user_name?: string;
  is_admin?: boolean;
  csrf_token?: string;
}

interface LoginPageProps {
  onSuccess: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onSuccess }) => {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Заполните все поля');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await apiPost<LoginResponse>('/rost_max/login', { email, password });
      if (data.error) {
        setError(data.error);
      } else {
        // Сессия отротирована (sid изменился) -> старый window.csrf_token из
        // HTML больше невалиден. Обновляем токен из ответа, иначе первый POST
        // (например сейв оценки) упадёт с "CSRF validation failed".
        if (data.csrf_token) {
          (window as unknown as { csrf_token?: string }).csrf_token = data.csrf_token;
        }
        onSuccess();
      }
    } catch {
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel 
      mode="card" 
      centered
      style={{ 
        height: '100dvh', 
        background: 'linear-gradient(135deg, var(--background-surface-ground) 0%, var(--background-surface-secondary) 100%)',
        padding: '24px'
      }}
    >
      <div 
        style={{ 
          width: '100%',
          maxWidth: '360px',
          backgroundColor: 'var(--background-surface-card)', 
          borderRadius: '16px',
          padding: '32px 24px',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.05)',
          border: '1px solid var(--stroke-separator-secondary)'
        }}
      >
        <form onSubmit={handleLogin}>
          <Flex direction="column" gap={24}>
            <Flex direction="column" gap={8} align="center" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '40px', marginBottom: '8px' }}>🎓</div>
              <Title level="1" weight="2" style={{ color: 'var(--text-primary)' }}>
                Школа РОСТ
              </Title>
              <Text weight="1" style={{ color: 'var(--text-secondary)' }}>
                Войдите в свой аккаунт мини-приложения
              </Text>
            </Flex>

            <Flex direction="column" gap={14}>
              <Flex direction="column" gap={6}>
                <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)' }}>Email</label>
                <Input
                  placeholder="name@school.ru"
                  type="email"
                  value={email}
                  onChange={e => setEmail((e.target as HTMLInputElement).value)}
                  disabled={loading}
                  style={{ width: '100%' }}
                />
              </Flex>
              
              <Flex direction="column" gap={6}>
                <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)' }}>Пароль</label>
                <Input
                  placeholder="••••••••"
                  type="password"
                  value={password}
                  onChange={e => setPassword((e.target as HTMLInputElement).value)}
                  disabled={loading}
                  style={{ width: '100%' }}
                />
              </Flex>
            </Flex>

            {error && (
              <div 
                style={{ 
                  backgroundColor: 'var(--background-accent-negative)', 
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--stroke-negative)'
                }}
              >
                <Text weight="1" style={{ color: 'var(--text-negative)', fontSize: '13px', lineHeight: '1.4' }}>
                  ⚠️ {error}
                </Text>
              </div>
            )}

            <Button 
              type="submit"
              mode="primary"
              disabled={loading}
              style={{ width: '100%', height: '44px', borderRadius: '8px', fontWeight: 600 }}
            >
              {loading ? 'Проверка данных...' : 'Войти'}
            </Button>
          </Flex>
        </form>
      </div>
    </Panel>
  );
};
