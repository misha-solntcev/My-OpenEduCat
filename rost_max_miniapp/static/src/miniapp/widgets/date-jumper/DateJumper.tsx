import React from 'react';
import { Input } from '@maxhub/max-ui';

interface DateJumperProps {
  value: string;
  onChange: (value: string) => void;
}

/**
 * Единый селектор даты (Date Jumper). Используется на дашборде и расписании,
 * чтобы выбор даты был синхронизирован через общий стор (app/store.ts).
 * Нативный Input из @maxhub/max-ui (сам рисует карточку + iconBefore).
 */
export const DateJumper: React.FC<DateJumperProps> = ({ value, onChange }) => (
  <Input
    type="date"
    value={value}
    onChange={e => onChange(e.target.value)}
    iconBefore={<span style={{ fontSize: '18px' }}>📅</span>}
    mode="primary"
    style={{ width: '100%' }}
  />
);
