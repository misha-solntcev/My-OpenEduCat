import React from 'react';
import { Flex } from '@maxhub/max-ui';

interface DateJumperProps {
  value: string;
  onChange: (value: string) => void;
}

/**
 * Единый селектор даты (Date Jumper). Используется на дашборде и расписании,
 * чтобы выбор даты был синхронизирован через общий стор (app/store.ts).
 */
export const DateJumper: React.FC<DateJumperProps> = ({ value, onChange }) => (
  <Flex align="center" gap={10} className="rm-card rm-card--dash" style={{ padding: '10px 14px' }}>
    <span style={{ fontSize: '18px' }}>📅</span>
    <input
      type="date"
      value={value}
      onChange={e => onChange(e.target.value)}
      className="rm-input"
      style={{
        flex: 1,
        border: 'none',
        backgroundColor: 'transparent',
        color: 'var(--text-primary)',
        fontSize: '15px',
        fontWeight: 600,
        outline: 'none',
        fontFamily: 'inherit',
      }}
    />
  </Flex>
);
