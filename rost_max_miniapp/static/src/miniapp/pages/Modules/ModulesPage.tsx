import React from 'react';
import { Flex, Typography, Panel } from '@maxhub/max-ui';

/**
 * Экран «Модули» — точка расширения для будущих модулей мини-приложения
 * (например, доп. разделы, настройки, отчёты). Пока заглушка: показываем
 * понятный пустой экран вместо инлайн-строки в роутере.
 */
export const ModulesPage: React.FC = () => {
  return (
    <Flex direction="column" align="stretch" gap={12} style={{ width: '100%' }}>
      <Panel mode="secondary" style={{ padding: '24px', borderRadius: '16px' }}>
        <Flex direction="column" align="center" gap={12} style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '48px' }}>⚡</div>
          <Typography.Title variant="small-strong">
            Модули
          </Typography.Title>
          <Typography.Body variant="small" style={{ color: 'var(--text-secondary)', margin: 0 }}>
            Раздел в разработке. Здесь появятся дополнительные модули мини-приложения.
          </Typography.Body>
        </Flex>
      </Panel>
    </Flex>
  );
};
