import React from 'react';
import { Flex, ToolButton } from '@maxhub/max-ui';

interface TabBarProps {
  currentTab?: string;
  onTabChange: (tabId: string) => void;
}

const TABS = [
  { id: 'dashboard', icon: '🏠', label: 'Главная' },
  { id: 'timetable', icon: '📅', label: 'Расписание' },
  { id: 'modules', icon: '⚡', label: 'Модули' },
];

/**
 * Нижний таб-бар приложения. Выделен из Layout, чтобы Layout остался чистой
 * обёрткой контента, а навигация жила в переиспользуемом виджете.
 */
export const TabBar: React.FC<TabBarProps> = ({ currentTab, onTabChange }) => (
  <Flex
    justify="space-around"
    align="center"
    style={{
      width: '100%',
      height: '64px',
      backgroundColor: 'var(--background-surface-card)',
      borderTop: '1px solid var(--stroke-separator-secondary)',
      position: 'absolute',
      bottom: 0,
      left: 0,
      zIndex: 10,
      boxShadow: '0 -4px 16px rgba(0, 0, 0, 0.06)',
      padding: '0 8px',
      boxSizing: 'border-box',
    }}
  >
    {TABS.map(tab => (
      <ToolButton
        key={tab.id}
        icon={<span style={{ fontSize: '18px' }}>{tab.icon}</span>}
        appearance={currentTab === tab.id ? 'secondary' : 'default'}
        onClick={() => onTabChange(tab.id)}
      >
        {tab.label}
      </ToolButton>
    ))}
  </Flex>
);
