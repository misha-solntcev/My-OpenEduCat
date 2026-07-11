import React from 'react';
import { Flex, ToolButton } from '@maxhub/max-ui';

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
            borderTop: '1px solid var(--stroke-separator-secondary)',
            position: 'absolute',
            bottom: 0,
            left: 0,
            zIndex: 10,
            boxShadow: '0 -4px 16px rgba(0, 0, 0, 0.06)',
            padding: '0 8px',
            boxSizing: 'border-box'
          }}
        >
          <ToolButton
            icon={<span style={{ fontSize: '18px' }}>🏠</span>}
            appearance={currentTab === 'dashboard' ? 'secondary' : 'default'}
            onClick={() => onTabChange('dashboard')}
          >
            Главная
          </ToolButton>
          <ToolButton
            icon={<span style={{ fontSize: '18px' }}>📅</span>}
            appearance={currentTab === 'timetable' ? 'secondary' : 'default'}
            onClick={() => onTabChange('timetable')}
          >
            Расписание
          </ToolButton>
          <ToolButton
            icon={<span style={{ fontSize: '18px' }}>⚡</span>}
            appearance={currentTab === 'modules' ? 'secondary' : 'default'}
            onClick={() => onTabChange('modules')}
          >
            Модули
          </ToolButton>
        </Flex>
      )}
    </Flex>
  );
};