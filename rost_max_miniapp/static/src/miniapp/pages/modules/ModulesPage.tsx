import React from 'react';
import {
  Panel,
  PanelHeader,
  Button,
  Separator,
} from '@vkontakte/vkui';


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
