import React from 'react';
import { Panel, PanelHeader, Placeholder, Text } from '@vkontakte/vkui';

export const ModulesPage: React.FC<{ id: string }> = ({ id }) => {
  return (
    <Panel id={id}>
      <PanelHeader>Модули</PanelHeader>
      <Placeholder icon="🚧" title="Страница в разработке">
        <Text>Здесь появятся модули приложения.</Text>
      </Placeholder>
    </Panel>
  );
};
