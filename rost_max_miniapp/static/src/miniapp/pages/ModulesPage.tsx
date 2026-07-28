import React from 'react';
import { Panel, PanelHeader, Flex, Title, Text } from '@vkontakte/vkui';

/**
 * Экран «Модули» — точка расширения для будущих модулей мини-приложения
 * (например, доп. разделы, настройки, отчёты). Пока заглушка: показываем
 * понятный пустой экран вместо инлайн-строки в роутере.
 */
export const ModulesPage: React.FC = () => {
  return (
    <Panel id="modules-panel">
      <PanelHeader>Модули</PanelHeader>
      <Flex direction="column" align="stretch" gap={12} style={{ width: '100%' }}>
        <Panel mode="card" style={{ padding: '24px', borderRadius: '16px' }}>
          <Flex direction="column" align="center" gap={12} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '48px' }}>⚡</div>
            <Title level="3" weight="2">
              Модули
            </Title>
            <Text weight="1" style={{ color: 'var(--text-secondary)', margin: 0 }}>
              Раздел в разработке. Здесь появятся дополнительные модули мини-приложения.
            </Text>
          </Flex>
        </Panel>
      </Flex>
    </Panel>
  );
};
