import React from 'react';
import { Flex, Typography } from '@maxhub/max-ui';

const tabButtonStyle = (isActive: boolean) => ({
  background: isActive ? 'rgba(0, 122, 255, 0.08)' : 'none',
  border: 'none',
  borderRadius: '12px',
  padding: '6px 12px',
  margin: '4px',
  display: 'flex',
  flexDirection: 'column' as const,
  alignItems: 'center',
  justifyContent: 'center',
  gap: '2px',
  height: 'calc(100% - 8px)',
  color: isActive ? 'var(--brand-default, #007aff)' : 'var(--text-muted, #8e8e93)',
  cursor: 'pointer',
  transition: 'all 0.2s ease'
});

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  currentTab?: string;
  onTabChange?: (tab: string) => void;
}

export const Layout: React.FC<LayoutProps> = ({ 
  children, 
  title = 'Школа РОСТ', 
  currentTab, 
  onTabChange 
}) => {
  return (
    <Flex 
      direction="column" 
      align="stretch"
      style={{ 
        width: '100%', 
        height: '100dvh', 
        backgroundColor: 'var(--background-surface-ground)',
        overflow: 'hidden',
        position: 'relative'
      }}
    >
      {/* Верхний Header удалён: MAX-клиент сам показывает заголовок,
          чтобы не было двойного хедера и экономить вертикальное место */}

      {/* Контентная зона со скроллом */}
      <div 
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          padding: '16px',
          WebkitOverflowScrolling: 'touch',
          paddingBottom: currentTab ? '80px' : '16px'
        }}
      >
        {children}
      </div>

      {/* Нижний Таб-бар */}
      {currentTab && onTabChange && (
        <Flex 
          justify="space-around" 
          align="center"
          style={{ 
            width: '100%',
            height: '64px', 
            backgroundColor: 'var(--background-surface-card)',
            borderTop: '1px solid var(--border-neutral-subtle)',
            position: 'absolute',
            bottom: 0,
            left: 0,
            zIndex: 10,
            boxShadow: '0 -4px 16px rgba(0, 0, 0, 0.06)',
            padding: '0 8px',
            boxSizing: 'border-box'
          }}
        >
          <button onClick={() => onTabChange('dashboard')} style={tabButtonStyle(currentTab === 'dashboard')}>
            <div style={{ fontSize: '18px' }}>🏠</div>
            <div style={{ fontSize: '11px' }}>Главная</div>
          </button>
          <button onClick={() => onTabChange('timetable')} style={tabButtonStyle(currentTab === 'timetable')}>
            <div style={{ fontSize: '18px' }}>📅</div>
            <div style={{ fontSize: '11px' }}>Расписание</div>
          </button>
          <button onClick={() => onTabChange('modules')} style={tabButtonStyle(currentTab === 'modules')}>
            <div style={{ fontSize: '18px' }}>⚡</div>
            <div style={{ fontSize: '11px' }}>Модули</div>
          </button>
        </Flex>
      )}
    </Flex>
  );
};