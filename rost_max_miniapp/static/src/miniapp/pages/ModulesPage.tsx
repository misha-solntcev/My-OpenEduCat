import React from 'react';
import {
  Panel,
  PanelHeader,
  Flex,
  Title,
  Text,
  IconButton,
  Button,
  ButtonGroup,
  Separator,
  Subhead,
  Group,
  Card,
  Caption,
} from '@vkontakte/vkui';
import {
  Icon28CalendarOutline,
  Icon28UsersOutline,
} from '@vkontakte/icons';

/**
 * Экран «Модули» — дизайн-примеры для выбора подхода к фильтрам TimetablePage
 */
export const ModulesPage: React.FC<{ id: string }> = ({ id }) => {
  return (
    <Panel id={id}>
      <PanelHeader>Дизайн-примеры</PanelHeader>
      
      {/* Вариант A: Кнопки в header */}
      <Group
        header={
          <Caption level="1" weight="1" style={{ color: 'var(--vkui--color_text_accent)' }}>
            ВАРИАНТ A: Кнопки в PanelHeader
          </Caption>
        }        
      >
        <Card mode="outline">
          {/* PanelHeader mockup */}
          <Flex
            justify="space-between"
            align="center"
            style={{
              padding: '12px 16px',
              borderBottom: '0.5px solid var(--vkui--color_separator_primary)',
            }}
          >
            <Title level="2" weight="2">Расписание</Title>
            <Flex gap={4}>
              <IconButton label="Выбрать дату">
                <Icon28CalendarOutline />
              </IconButton>
              <IconButton label="Выбрать учителя">
                <Icon28UsersOutline />
              </IconButton>
            </Flex>
          </Flex>

          {/* Content preview */}
          <Flex style={{ padding: '16px' }}>
            <Text style={{ color: 'var(--vkui--color_text_secondary)' }}>
              Список занятий появится здесь...
            </Text>
          </Flex>
        </Card>
      </Group>

      <Separator />

      {/* Вариант B: Subhead с inline-фильтрами */}
      <Group
        header={
          <Caption level="1" weight="1" style={{ color: 'var(--vkui--color_text_accent)' }}>
            ВАРИАНТ B: Subhead с inline-фильтрами
          </Caption>
        }        
      >
        <Card mode="outline">
          {/* PanelHeader mockup */}
          <Flex
            justify="space-between"
            align="center"
            style={{
              padding: '12px 16px',
              borderBottom: '0.5px solid var(--vkui--color_separator_primary)',
            }}
          >
            <Title level="2" weight="2">Расписание</Title>
          </Flex>

          {/* Subhead with filters */}
          <Flex
            direction="column"
            gap={12}
            style={{
              padding: '12px 16px',
              background: 'var(--vkui--color_background_secondary)',
              borderBottom: '0.5px solid var(--vkui--color_separator_primary)',
            }}
          >
            {/* Учитель */}
            <Flex align="center" gap={8}>
              <Subhead weight="2" style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Учитель:
              </Subhead>
              <Button mode="secondary" size="m">
                Все учителя
              </Button>
            </Flex>

            {/* Дата */}
            <Flex align="center" gap={8}>
              <Subhead weight="2" style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Дата:
              </Subhead>
              <ButtonGroup mode="horizontal" gap="s">
                <Button mode="secondary" size="m">←</Button>
                <Button mode="secondary" size="m" stretched style={{ minWidth: 120 }}>
                  28 июля
                </Button>
                <Button mode="secondary" size="m">→</Button>
              </ButtonGroup>
            </Flex>
          </Flex>

          {/* Content preview */}
          <Flex style={{ padding: '16px' }}>
            <Text style={{ color: 'var(--vkui--color_text_secondary)' }}>
              Список занятий появится здесь...
            </Text>
          </Flex>
        </Card>
      </Group>

    </Panel>
  );
};
