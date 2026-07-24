import React from 'react';
import { Flex, Title, Text } from '@vkontakte/vkui';

interface EmptyStateProps {
  icon?: string;
  title: string;
  subtitle: string;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * Универсальное пустое состояние (нет данных).
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = '🍃',
  title,
  subtitle,
  className,
  style,
}) => (
  <Flex
    direction="column"
    align="center"
    justify="center"
    className={`rm-card rm-card--empty ${className || ''}`}
    style={{
      paddingBottom: '24px',
      ...style,
    }}
  >
    <div style={{ fontSize: '48px', marginBottom: '12px' }}>{icon}</div>
    <Title level="3" weight="2">
      {title}
    </Title>
    <Text weight="1" style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>
      {subtitle}
    </Text>
  </Flex>
);