import React from 'react';
import {
  Panel,
  PanelHeader,
  Button,
  Separator,
  Spacing,
} from '@vkontakte/vkui';


export const ModulesPage: React.FC<{ id: string }> = ({ id }) => {
  return (
    <Panel id={id} mode="card" centered >
      <PanelHeader>Песочница</PanelHeader>
      <Button size="s" mode="primary" onClick={() => alert('Hello, World!')}>
        Hello, World!
      </Button>
      <Spacing />
      <Button mode="outline" size="m"  >
        Hello, World!
      </Button>
      <Spacing />
      <Button size="l" >
        Hello, World!
      </Button>
      <Separator size={"s"}/>
      <Button size="m" >
        Hello, World!
      </Button>
      <Separator size={"m"}/>
      <Button size="m" >
        Hello, World!
      </Button>
      <Separator size={"l"}/>
      <Button size="m" >
        Hello, World!
      </Button>
      <Separator size={"l"}/>      
    </Panel>
  );
};
