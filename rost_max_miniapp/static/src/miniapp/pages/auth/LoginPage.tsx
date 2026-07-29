import React from 'react';
import {
  Panel,
  Box,
  Group,
  FormItem,
  FormLayoutGroup,
  FormStatus,
  Input,
  Button,
  Checkbox,
  Link,
  Flex,
} from '@vkontakte/vkui';
import { apiPost } from '@/shared/lib';
import { useAppStore } from '@/shared/lib/store';

interface LoginResponse {
  success?: boolean;
  error?: string;
  user_name?: string;
  is_admin?: boolean;
  csrf_token?: string;
  // 2FA fields
  require_2fa?: boolean;
  two_factor_enabled?: boolean;
}

interface LoginPageProps {
  id: string;
}

// Получаем CSRF токен из window (инъекция из templates.xml)
const getCsrfToken = (): string => {
  const fromWindow = (window as unknown as { csrf_token?: string }).csrf_token;
  if (fromWindow) return fromWindow;
  return document.cookie
    .split('; ')
    .find(r => r.startsWith('csrf_token='))
    ?.split('=')[1] || '';
};

export const LoginPage: React.FC<LoginPageProps> = ({ id }) => {
  const [login, setLogin] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [totpCode, setTotpCode] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [step, setStep] = React.useState<'password' | 'totp'>('password');
  const [totpTrusted, setTotpTrusted] = React.useState(false);

  const setAuthSuccess = useAppStore(s => s.setAuthSuccess);
  const loadUserInfo = useAppStore(s => s.loadUserInfo);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (step === 'password') {
      if (!login || !password) {
        setError('Заполните все поля');
        return;
      }
    } else {
      if (!totpCode || totpCode.length !== 6) {
        setError('Введите 6-значный код');
        return;
      }
    }

    setLoading(true);

    try {
      const csrfToken = getCsrfToken();
      const payload = step === 'password'
        ? { login, password, csrf_token: csrfToken }
        : { totp_code: totpCode, trusted_device: totpTrusted, csrf_token: csrfToken };

      const data = await apiPost<LoginResponse>(
        step === 'password' ? '/rost_max/login' : '/rost_max/login/totp',
        payload
      );

      if (data.error) {
        setError(data.error);
        return;
      }

      // 2FA challenge
      if (data.require_2fa || data.two_factor_enabled) {
        setStep('totp');
        setError(null);
        return;
      }

      // Успешный логин — загружаем профиль ПЕРЕД переключением на main
      if (data.csrf_token) {
        (window as unknown as { csrf_token?: string }).csrf_token = data.csrf_token;
      }
      await loadUserInfo();
      setAuthSuccess(true);
    } catch {
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToPassword = () => {
    setStep('password');
    setTotpCode('');
    setError(null);
  };

  const handleForgotPassword = (e: React.MouseEvent) => {
    e.preventDefault();
    // Редирект на Odoo reset password с возвратом в SPA
    const redirect = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/web/reset_password?redirect=${redirect}`;
  };

  return (
    <Panel id={id} mode="card">      
      <Flex direction="column" justify="center" align="center" style={{ minHeight: '100vh' }}>
        <Box maxInlineSize={420} paddingInline="m">
          <Group>
            <form onSubmit={handleLogin}>
              <input type="hidden" name="type" value="password" />
              <input type="hidden" name="csrf_token" value={getCsrfToken()} />

              <FormLayoutGroup>
                {step === 'password' && (
                  <>
                    <FormItem top="Логин" htmlFor="login-input">
                      <Input
                        id="login-input"
                        name="login"
                        type="text"
                        autoComplete="username"
                        placeholder="name@rostschoolspb.ru"
                        value={login}
                        onChange={e => setLogin(e.target.value)}
                        disabled={loading}
                        autoFocus
                      />
                    </FormItem>

                    <FormItem top="Пароль" htmlFor="password-input">
                      <Input
                        id="password-input"
                        name="password"
                        type="password"
                        autoComplete="current-password"
                        placeholder="••••••••"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        disabled={loading}
                      />
                    </FormItem>

                    {error && (
                      <FormItem>
                        <FormStatus mode="error" title="Ошибка входа">
                          {error}
                        </FormStatus>
                      </FormItem>
                    )}
                  </>
                )}

                {step === 'totp' && (
                  <>
                    <FormItem top="Код из приложения" htmlFor="totp-input">
                      <Input
                        id="totp-input"
                        name="totp_code"
                        type="text"
                        autoComplete="one-time-code"
                        inputMode="numeric"
                        maxLength={6}
                        placeholder="123456"
                        value={totpCode}
                        onChange={e => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        disabled={loading}
                        autoFocus
                      />
                    </FormItem>

                    <FormItem>
                      <Checkbox
                        checked={totpTrusted}
                        onChange={e => setTotpTrusted(e.target.checked)}
                      >
                        Не спрашивать на этом устройстве (90 дней)
                      </Checkbox>
                    </FormItem>
                  </>
                )}
              </FormLayoutGroup>

              {step === 'password' && (
                <>
                  <FormItem>
                    <Button size="l" stretched mode="primary" type="submit" loading={loading}>
                      Войти
                    </Button>
                  </FormItem>

                  <FormItem>
                    <Flex justify="center">
                      <Link onClick={handleForgotPassword} noUnderline>
                        Забыли пароль?
                      </Link>
                    </Flex>
                  </FormItem>
                </>
              )}

              {step === 'totp' && (
                <>
                  <FormItem>
                    <Button size="l" stretched mode="primary" type="submit" loading={loading}>
                      Подтвердить
                    </Button>
                  </FormItem>

                  <FormItem>
                    <Button
                      size="l"
                      stretched
                      mode="secondary"
                      type="button"
                      onClick={handleBackToPassword}
                    >
                      Назад
                    </Button>
                  </FormItem>
                </>
              )}
            </form>
          </Group>
        </Box>
      </Flex>
    </Panel>
  );
};