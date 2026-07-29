import React from 'react';
import {
  Panel,
  PanelHeader,
  Flex,
} from '@vkontakte/vkui';
import {
  Icon28CalendarOutline,
  Icon28UsersOutline,
} from '@vkontakte/icons';


export const ModulesPage: React.FC<{ id: string }> = ({ id }) => {
  return (
    <Panel id={id}>
      <PanelHeader>Дизайн-примеры</PanelHeader>      
      <Flex
        direction="column"
        gap="m"
        style={{
          padding: '16px',
        }}
      > 
      </Flex>
    </Panel>
  );
};
