import React from 'react';
import { Flex } from '@vkontakte/vkui';

interface LayoutProps {
  children: React.ReactNode;
}

/**
 * Чистая обёртка контента приложения. Верхний хедер не нужен (MAX-клиент
 * сам показывает заголовок). Нижний таб-бар рендерится на уровне app
 * (app/App.tsx) через widgets/tab-bar, т.к. shared не может импортировать widgets.
 */
export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <Flex
      direction="column"
      align="stretch"
      style={{
        width: '100%',
        height: '100dvh',
        backgroundColor: 'var(--background-surface-ground)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          WebkitOverflowScrolling: 'touch',
          paddingBottom: '80px',
        }}
      >
        {children}
      </div>
    </Flex>
  );
};
