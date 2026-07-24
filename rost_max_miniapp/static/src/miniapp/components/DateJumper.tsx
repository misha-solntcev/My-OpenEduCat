import React from 'react';
import { Input } from '@vkontakte/vkui';

interface DateJumperProps {
  value: string;
  onChange: (value: string) => void;
}

/**
 * Единый селектор даты (Date Jumper). Используется на дашборде и расписании,
 * чтобы выбор даты был синхронизирован через общий стор (app/store.ts).
 * Нативный Input из @vkontakte/vkui (сам рисует карточку + before).
 */
export const DateJumper: React.FC<DateJumperProps> = ({ value, onChange }) => (
  <Input
    type="date"
    value={value}
    onChange={e => onChange(e.target.value)}
    before={<span style={{ fontSize: '18px' }}>📅</span>}
    mode="default"
  />
);