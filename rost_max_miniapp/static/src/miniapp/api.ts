// API-клиент для rost_max_miniapp

function getCsrfToken(): string {
  return document.cookie
    .split('; ')
    .find(r => r.startsWith('csrf_token='))
    ?.split('=')[1] || '';
}

export async function apiGet<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    headers: { 'X-CSRF-TOKEN': getCsrfToken() },
  });
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
  return res.json();
}
