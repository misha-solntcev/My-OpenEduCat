import React from 'react';
import { Placeholder } from '@vkontakte/vkui';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  subtitle: string;
  action?: React.ReactNode;
}

/**
 * Универсальное пустое состояние (нет данных).
 * Использует VKUI Placeholder вместо кастомных CSS-классов.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = '🍃',
  title,
  subtitle,
  action,
}) => (
  <Placeholder
    icon={icon}
    title={title}
    action={action}
    stretched
  >
    {subtitle}
  </Placeholder>
);