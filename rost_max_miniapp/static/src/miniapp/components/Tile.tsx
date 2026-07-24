import React from 'react';
import { Flex, Title, Text } from '@vkontakte/vkui';

interface TileProps {
  icon: string;
  label: string;
  value: React.ReactNode;
}

// Плитка метрики 2x2 дашборда: иконка сверху по центру + название (мелко)
// и значение (крупно) снизу. Весь стиль — инлайн, чтобы было наглядно и под
// контролем; токены темозависимы (var(--...)).
export const Tile: React.FC<TileProps> = ({ icon, label, value }) => (
  <Flex
    direction="column"
    align="center"
    justify="center"
    gap={4}
    style={{
      padding: '14px',
      backgroundColor: 'var(--background-surface-card)',
      borderRadius: 'var(--size-border-radius-semantic-border-radius-card)',
      border: '1px solid var(--stroke-separator-secondary)',
    }}
  >
    <span style={{ fontSize: '18px' }}>{icon}</span>
    <Text weight="2" style={{ textAlign: 'center' }}>
      {label}
    </Text>
    <Title level="3" weight="2" style={{ textAlign: 'center' }}>
      {value}
    </Title>
  </Flex>
);
