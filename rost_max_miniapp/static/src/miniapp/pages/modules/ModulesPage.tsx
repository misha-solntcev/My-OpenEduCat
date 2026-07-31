import React from 'react';
import {
  Panel,
  PanelHeader,
  Button,
  Separator,
  Spacing,
  Cell,
  List,
} from '@vkontakte/vkui';
import { Icon28Settings, Icon28User } from '@vkontakte/icons';


export const ModulesPage: React.FC<{ id: string }> = ({ id }) => {
  return (
    <Panel id={id} mode="card" centered >
      <PanelHeader>Песочница</PanelHeader>      
      <Button mode="outline" size="m"  >
        Hello, World!
      </Button>     

      <Separator size={"l"} />      

    </Panel>
  );
};
