/**
 * SegmentedControl с акцентным слайдером и счётчиками — единый
 * сегмент-контрол приложения (страницы «Задания» ученика и учителя,
 * очередь проверки ReviewQueue).
 *
 * Механика: фон слайдера в VKUI — токен --vkui--color_segmented_control.
 * Пропа для его перекраски нет, поэтому токен переопределяется на хосте —
 * CSS-переменная каскадом доходит до .slider. ЭТО НЕЗАДОКУМЕНТИРОВАННЫЙ
 * ПУТЬ: если после обновления VKUI слайдер перестанет брать цвет из
 * каскада, чинить нужно только здесь.
 *
 * Активная опция: белый текст + контрастный (белый на синем) счётчик.
 * Неактивные: обычный текст + синяя цифра без заливки.
 */
import React from 'react';
import { SegmentedControl, Counter } from '@vkontakte/vkui';

export interface AccentSegmentOption<T extends string> {
  value: T;
  title: string;
  count?: number | undefined;
}

interface Props<T extends string> {
  value: T;
  onChange: (v: T) => void;
  options: AccentSegmentOption<T>[];
  style?: React.CSSProperties | undefined;
  'aria-label'?: string | undefined;
}

export const AccentSegmentedControl = <T extends string>({
  value, onChange, options, style, ...rest
}: Props<T>): React.ReactNode => (
  <SegmentedControl
    role="tablist"
    value={value}
    onChange={v => onChange(v as T)}
    style={{
      ...style,
      '--vkui--color_segmented_control': 'var(--vkui--color_background_accent)',
    } as React.CSSProperties}
    options={options.map(opt => ({
      label: (
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          color: opt.value === value ? 'var(--vkui--color_text_contrast)' : undefined,
        }}>
          {opt.title}
          {opt.count != null && (
            <Counter
              size="s"
              mode={opt.value === value ? 'contrast' : 'tertiary'}
              appearance="accent"
            >
              {opt.count}
            </Counter>
          )}
        </span>
      ),
      value: opt.value,
    }))}
    {...rest}
  />
);
