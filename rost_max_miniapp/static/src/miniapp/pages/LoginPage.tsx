import React from 'react';
import { Panel, Flex, Typography, Button, Input } from '@maxhub/max-ui';
import { apiPost } from '../api';

interface LoginResponse {
  success?: boolean;
  error?: string;
  user_name?: string;
  is_admin?: boolean;
}

export const LoginPage: React.FC = () => {
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
        window.location.href = '/rost_max/dashboard';
      }
    } catch {
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel 
      mode="secondary" 
      centeredX 
      centeredY 
      style={{ 
        height: '100dvh', 
        background: 'linear-gradient(135deg, var(--background-surface-ground) 0%, var(--background-neutral-subtle) 100%)',
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
          border: '1px solid var(--border-neutral-subtle)'
        }}
      >
        <form onSubmit={handleLogin}>
          <Flex direction="column" gap={24}>
            <Flex direction="column" gap={8} align="center" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '40px', marginBottom: '8px' }}>🎓</div>
              <Typography.Title level={2} style={{ margin: 0, fontWeight: 700, color: 'var(--text-default)' }}>
                Школа РОСТ
              </Typography.Title>
              <Typography.Body size="small" style={{ color: 'var(--text-muted)' }}>
                Войдите в свой аккаунт мини-приложения
              </Typography.Body>
            </Flex>

            <Flex direction="column" gap={14}>
              <Flex direction="column" gap={6}>
                <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-muted)' }}>Email</label>
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
                <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-muted)' }}>Пароль</label>
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
                  backgroundColor: 'var(--background-negative-subtle)', 
                  padding: '10px 12px', 
                  borderRadius: '8px',
                  border: '1px solid var(--border-negative-subtle)'
                }}
              >
                <Typography.Body style={{ color: 'var(--text-negative)', fontSize: '13px', lineHeight: '1.4' }}>
                  ⚠️ {error}
                </Typography.Body>
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