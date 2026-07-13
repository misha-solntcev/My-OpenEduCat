import React from 'react';
import { Flex, Typography } from '@maxhub/max-ui';

// Нативный аналог «Card» (в MAX UI его нет; есть только Panel/Container/CellList).
// Composable API как в shadcn/ui / MUI: Card + CardHeader/Title/Description/Content/Footer.
// Все токены — из @maxhub/max-ui (темозависимы: светлая/тёмная темы подхватываются автоматически).

type Align = 'start' | 'center' | 'end';

interface CardProps {
  children?: React.ReactNode;
  bordered?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export const Card: React.FC<CardProps> = ({ children, bordered = true, className, style }) => (
  <div
    className={className}
    style={{
      backgroundColor: 'var(--background-surface-card)',
      borderRadius: 'var(--size-border-radius-semantic-border-radius-card)',
      border: bordered ? '1px solid var(--stroke-separator-secondary)' : 'none',
      boxShadow: '0 1px 4px rgba(0, 0, 0, 0.02)',
      padding: '16px',
      boxSizing: 'border-box',
      width: '100%',
      ...style,
    }}
  >
    {children}
  </div>
);

interface CardHeaderProps {
  media?: React.ReactNode;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  direction?: 'horizontal' | 'vertical';
  align?: Align;
  justify?: Align;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  media,
  title,
  description,
  action,
  direction = 'horizontal',
  align = 'center',
  justify = 'start',
  className,
}) => (
  <Flex
    direction={direction}
    align={align}
    justify={justify}
    gap={direction === 'vertical' ? 8 : 12}
    className={className}
    style={{ marginBottom: description || action ? '12px' : 0, width: '100%' }}
  >
    {media && (
      <Flex align="center" justify="center" style={{ flexShrink: 0 }}>
        {media}
      </Flex>
    )}
    <Flex
      direction="column"
      gap={2}
      style={{ minWidth: 0, flex: action ? 1 : undefined, alignItems: align }}
    >
      {title != null && <CardTitle>{title}</CardTitle>}
      {description != null && <CardDescription>{description}</CardDescription>}
    </Flex>
    {action && (
      <Flex align="center" style={{ flexShrink: 0 }}>
        {action}
      </Flex>
    )}
  </Flex>
);

export const CardTitle: React.FC<{ children?: React.ReactNode; className?: string }> = ({ children, className }) => (
  <Typography.Title
    variant="small-strong"
    className={className}
    style={{ margin: 0, fontWeight: 700, color: 'var(--text-primary)' }}
  >
    {children}
  </Typography.Title>
);

export const CardDescription: React.FC<{ children?: React.ReactNode; className?: string }> = ({ children, className }) => (
  <Typography.Body
    variant="small"
    className={className}
    style={{ color: 'var(--text-secondary)', fontWeight: 500 }}
  >
    {children}
  </Typography.Body>
);

export const CardContent: React.FC<{ children?: React.ReactNode; className?: string; style?: React.CSSProperties; align?: Align }> = ({
  children,
  className,
  style,
  align = 'stretch',
}) => (
  <Flex direction="column" align={align} className={className} style={style}>
    {children}
  </Flex>
);

export const CardFooter: React.FC<{ children?: React.ReactNode; className?: string; style?: React.CSSProperties }> = ({
  children,
  className,
  style,
}) => (
  <Flex className={className} style={{ marginTop: '12px', ...style }}>
    {children}
  </Flex>
);
