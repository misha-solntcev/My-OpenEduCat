// API-клиент для rost_max_miniapp

function getCsrfToken(): string {
  // Токен инъецируется сервером в window.csrf_token при рендере SPA
  // (views/templates.xml) и обновляется после логина (поле csrf_token в
  // ответе /rost_max/login). Fallback на куку на случай, если инъекция
  // не сработала. Пустая строка -> бэкенд вернёт "CSRF validation failed".
  const fromWindow = (window as unknown as { csrf_token?: string }).csrf_token;
  if (fromWindow) return fromWindow;
  return document.cookie
    .split('; ')
    .find(r => r.startsWith('csrf_token='))
    ?.split('=')[1] || '';
}

export async function apiGet<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    headers: { 'X-CSRF-TOKEN': getCsrfToken() },
  });

  if (res.status === 401 || res.status === 403) {
    window.location.href = '/rost_max/login';
    throw new Error('Session expired');
  }

  return res.json();
}

export async function apiPost<T>(url: string, data: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-TOKEN': getCsrfToken(),
    },
    body: JSON.stringify(data),
  });

  if (res.status === 401 || res.status === 403) {
    window.location.href = '/rost_max/login';
    throw new Error('Session expired');
  }

  return res.json();
}
