/**
 * Примитивы рельсы таймлайна (этап 2–3 редизайна): кружок-номер,
 * линия-соединитель, акцент-карточка состояния. Используется таймлайном
 * главной и таймлайном расписания.
 *
 * Стили: VKUI токены + инлайн, кастомных css-классов нет.
 */
import React from 'react';
import { Text, Caption } from '@vkontakte/vkui';

/** Кружок-номер слота.
 *  ВАЖНО: токен color_text_subheadline в VKUI 8 НЕ существует (есть
 *  color_text_subhead) — несуществующая var() даёт invalid color и текст
 *  наследует случайный цвет (на тёмной теме — чёрный на тёмном круге). */
export const RailNum: React.FC<{
  children: React.ReactNode;
  tone?: 'default' | 'past' | 'accent';
}> = ({ children, tone = 'default' }) => {
  const bg = tone === 'accent'
    ? 'var(--vkui--color_background_accent)'
    : 'var(--vkui--color_background_secondary)';
  const fg = tone === 'accent'
    ? 'var(--vkui--color_text_contrast)'
    : tone === 'past'
      ? 'var(--vkui--color_text_secondary)'
      : 'var(--vkui--color_text_subhead)';
  return (
    <div style={{
      width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
      background: bg, color: fg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 12, fontWeight: 700,
      zIndex: 2,
    }}>
      {children}
    </div>
  );
};

/** Линия-соединитель между кружками. Тянется от нижнего края своего
 *  кружка до верха следующего: слот задаёт рельсе marginBottom -20
 *  (свои 10px паддинга + 10px паддинга следующей строки), и линия
 *  переполняет строку ровно до следующего кружка (он её перекрывает).
 *  Цвета: обычная — icon_secondary (видна на обеих темах;
 *  separator_secondary на тёмной #141415 ≈ фон карточки #19191a —
 *  невидима), прошедшая — приглушённый separator_primary. */
export const RailLine: React.FC<{ dimmed?: boolean }> = ({ dimmed }) => (
  <div style={{
    flex: 1, width: 2, minHeight: 14,
    background: dimmed
      ? 'var(--vkui--color_separator_primary)'
      : 'var(--vkui--color_icon_secondary)',
    marginTop: 2,
  }} />
);

/**
 * Синяя акцент-карточка состояния: строка 1 = текст + время (жирно),
 * строка 2 — опциональный подзаголовок, затем полоса прогресса.
 * Акцент всегда синий (утверждено: не зелёный даже на «завершены»).
 */
export const LiveCard: React.FC<{
  text: React.ReactNode;
  after?: React.ReactNode;
  sub?: React.ReactNode;
  progress?: number;
}> = ({ text, after, sub, progress }) => (
  <div style={{
    background: 'var(--vkui--color_background_accent)',
    color: 'var(--vkui--color_text_contrast)',
    borderRadius: 10,
    padding: '9px 11px',
    marginTop: 6,
    boxShadow: '0 3px 10px rgba(38,136,235,.35)',
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
      <Text weight="2" style={{ fontSize: 13, color: 'inherit' }}>{text}</Text>
      {after != null && (
        <Text weight="2" style={{ fontSize: 13, color: 'inherit', flexShrink: 0 }}>{after}</Text>
      )}
    </div>
    {sub != null && (
      <Caption style={{ color: 'var(--vkui--color_text_contrast)', opacity: 0.8, display: 'block', marginTop: 2 }}>
        {sub}
      </Caption>
    )}
    {progress != null && (
      <div style={{
        height: 3, borderRadius: 2, overflow: 'hidden',
        background: 'rgba(255,255,255,.35)', marginTop: 7,
      }}>
        <div style={{
          height: '100%', width: `${Math.min(100, Math.max(0, progress))}%`,
          background: '#fff', borderRadius: 2,
        }} />
      </div>
    )}
  </div>
);

/** Инлайн-стили синей акцент-подложки — для слота таймлайна целиком
 *  (текущий урок красится синим от времени до прогресса, утверждено). */
export const accentSlotStyle: React.CSSProperties = {
  background: 'var(--vkui--color_background_accent)',
  color: 'var(--vkui--color_text_contrast)',
  borderRadius: 10,
  padding: '9px 11px',
  boxShadow: '0 3px 10px rgba(38,136,235,.35)',
};

/** Полоса прогресса (белая на синем) — хвост акцентного слота. */
export const AccentProgress: React.FC<{ progress: number }> = ({ progress }) => (
  <div style={{
    height: 3, borderRadius: 2, overflow: 'hidden',
    background: 'rgba(255,255,255,.35)', marginTop: 7,
  }}>
    <div style={{
      height: '100%', width: `${Math.min(100, Math.max(0, progress))}%`,
      background: '#fff', borderRadius: 2,
    }} />
  </div>
);

/** Имя-отчество: «Ермакова Лариса Анатольевна» -> «Лариса Анатольевна». */
export const firstNamePatronymic = (full: string): string => {
  const parts = (full || '').trim().split(/\s+/);
  return parts.length >= 3 ? parts.slice(1).join(' ') : full;
};

/** «09:30 - 10:15» -> [570, 615]; не распарсилось — null. */
export const timingToMinutes = (timing: string): [number, number] | null => {
  const parts = (timing || '').split(' - ');
  if (parts.length < 2) return null;
  const toMin = (s: string): number | null => {
    const m = s.trim().match(/^(\d{1,2}):(\d{2})$/);
    return m ? Number(m[1]) * 60 + Number(m[2]) : null;
  };
  const a = toMin(parts[0]);
  const b = toMin(parts[1]);
  return a != null && b != null ? [a, b] : null;
};

/** 610 -> «10:10» (без ведущего нуля часа, как в мокапе). */
export const fmtEnd = (min: number): string =>
  `${Math.floor(min / 60)}:${String(min % 60).padStart(2, '0')}`;
