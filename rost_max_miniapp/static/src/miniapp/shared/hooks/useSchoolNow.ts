/**
 * «Сейчас» по школьному времени с тиком. Возвращает минуты от полуночи
 * школьного дня, обновляет их раз в TICK_MS и при возврате из фона
 * (visibilitychange) — WebView может уснуть между тиками.
 *
 * Используется таймлайном главной: статус слота и прогресс урока
 * должны «ползти» сами, без перезагрузки ленты.
 */
import React from 'react';
import { schoolNowMinutes } from '@/shared/lib/date';

const TICK_MS = 30_000;

export const useSchoolNowMinutes = (): number => {
  const [now, setNow] = React.useState(schoolNowMinutes);

  React.useEffect(() => {
    const id = window.setInterval(() => setNow(schoolNowMinutes()), TICK_MS);
    const onVisible = () => {
      if (document.visibilityState === 'visible') setNow(schoolNowMinutes());
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  return now;
};
