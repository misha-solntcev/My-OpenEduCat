import React from 'react';
import { Flex, Typography, type FlexDirection, type FlexAlign, type FlexJustify } from '@maxhub/max-ui';

// Нативный аналог «Card» (в MAX UI его нет; есть только Panel/Container/CellList).
// Composable API как в shadcn/ui / MUI: Card + CardHeader/Title/Description/Content/Footer.
// Все токены — из @maxhub/max-ui (темозависимы: светлая/тёмная темы подхватываются автоматически).

interface CardProps {
  children?: React.ReactNode;
  bordered?: boolean;
  media?: React.ReactNode;
  text?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const Card: React.FC<CardProps> = ({ children, bordered = true, media, text, className, style }) => {
  const body = text != null ? <Typography.Body variant="small">{text}</Typography.Body> : children;
  return (
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
      {media != null ? (
        <Flex direction="row" align="center" gap={12} style={{ width: '100%' }}>
          <span style={{ flexShrink: 0 }}>{media}</span>
          <div style={{ minWidth: 0 }}>{body}</div>
        </Flex>
      ) : (
        body
      )}
    </div>
  );
};

interface CardHeaderProps {
  media?: React.ReactNode;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  direction?: FlexDirection;
  align?: FlexAlign;
  justify?: FlexJustify;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  media,
  title,
  description,
  action,
  direction = 'row',
  align = 'center',
  justify = 'start',
  className,
}) => (
  <Flex
    direction={direction}
    align={align}
    justify={justify}
    gap={direction === 'column' ? 8 : 12}
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

export const CardContent: React.FC<{ children?: React.ReactNode; className?: string; style?: React.CSSProperties; align?: FlexAlign }> = ({
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
