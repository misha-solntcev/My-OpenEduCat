import React from 'react';
import {
  Panel,
  PanelHeader,
  Text,
  Title,
  Button,
  SimpleCell,
  Avatar,
  Group,
  Placeholder,
} from '@vkontakte/vkui';
import { initialsOf } from '@/shared/lib/initials';
import { useAppStore } from '@/shared/lib/store';

export const DashboardPage: React.FC<{ id: string; onNavigate: (to: string) => void }> = ({ id }) => {
  const userInfo = useAppStore(s => s.userInfo);
  const userName = userInfo?.user_name ?? '';
  const isAdmin = userInfo?.is_admin ?? false;
  const isTeacher = userInfo?.is_teacher ?? false;
  const statusText = isAdmin ? 'Администратор' : isTeacher ? 'Преподаватель' : 'Ученик';

  // Fallback-имя, когда userInfo ещё не загружен
  const displayName = userName || statusText;
  const initials = initialsOf(displayName);

  return (
    <Panel id={id}>
      <PanelHeader>Главная</PanelHeader>

      {/* Кто авторизовался (временно; будет спрятан) */}
      <Group>
        <SimpleCell
          before={<Avatar size={40} initials={initials} gradientColor="blue" />}
          title={displayName}
          subtitle={statusText}
        />
      </Group>

      <Placeholder
        icon={<Title level="1">🚧</Title>}
        title="Страница в разработке"
        action={
          <Button
            mode="outline"
            appearance="negative"
            onClick={() => { window.location.href = '/rost_max/logout'; }}
          >
            Выйти
          </Button>
        }
      >
        <Text>Здесь появится главное меню приложения.</Text>
      </Placeholder>
    </Panel>
  );
};
