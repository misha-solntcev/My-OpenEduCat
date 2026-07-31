import React from 'react';
import { Card, Flex, Title, Text } from '@vkontakte/vkui';

interface TileProps {
  icon: string;
  label: string;
  value: React.ReactNode;
}

export const Tile: React.FC<TileProps> = ({ icon, label, value }) => (
  <Card>
    <Flex direction="column" align="center" gap={4} padding="m">
      <Text weight="2" size="l">{icon}</Text>
      <Text weight="2" align="center">
        {label}
      </Text>
      <Title level="3" weight="2" align="center">
        {value}
      </Title>
    </Flex>
  </Card>
);