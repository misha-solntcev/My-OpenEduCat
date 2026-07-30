import React from 'react';
import { Box } from '@vkontakte/vkui';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <Box style={{ backgroundColor: 'var(--vkui--color_background_surface_ground)', height: '100dvh', overflow: 'hidden' }}>
      <Box flexGrow={1} overflow="auto" padding="xl" paddingBlockEnd="80px">
        {children}
      </Box>
    </Box>
  );
};