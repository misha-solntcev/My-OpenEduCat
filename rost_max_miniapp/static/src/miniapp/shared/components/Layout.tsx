import React from 'react';
import { Box, Flex } from '@vkontakte/vkui';

interface LayoutProps {
  children: React.ReactNode;
}

/**
 * Чистая обёртка контента приложения.
 * Использует VKUI Box/Flex с токенами вместо inline-стилей.
 */
export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <Flex direction="column" height="100dvh" overflow="hidden" position="relative" style={{ backgroundColor: 'var(--background-surface-ground)' }}>
      <Box flexGrow={1} overflowBlock="auto" padding="xl" paddingBlockEnd="80px" style={{ WebkitOverflowScrolling: 'touch' }}>
        {children}
      </Box>
    </Flex>
  );
};
