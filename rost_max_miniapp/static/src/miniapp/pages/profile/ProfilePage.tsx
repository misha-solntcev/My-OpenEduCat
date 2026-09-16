/**
 * Профиль пользователя: аватар, имя, роль и выход из аккаунта.
 * Открывается тапом по аватару в приветствии на главной (View на уровне
 * Root, вне Epic — таббар не мешает). Кнопка «Выйти» живёт здесь, чтобы
 * не висеть fixed-плашкой поверх ленты главной.
 */
import React from 'react';
import {
  Panel,
  PanelHeader,
  PanelHeaderBack,
  Avatar,
  Text,
  Caption,
  Button,
  Div,
  Group,
  Header,
  SegmentedControl,
} from '@vkontakte/vkui';
import { useAppStore } from '@/shared/lib/store';
import { initialsOf } from '@/shared/lib/initials';
import type { ThemePreference } from '@/shared/lib/theme';

interface ProfilePageProps {
  id: string;
  onBack: () => void;
}

const roleLabel = (u: {
  is_admin: boolean;
  is_teacher: boolean;
  is_student: boolean;
  is_parent?: boolean;
} | null): string => {
  if (!u) return '';
  if (u.is_admin) return 'Администратор';
  if (u.is_teacher) return 'Преподаватель';
  if (u.is_parent) return 'Родитель';
  if (u.is_student) return 'Ученик';
  return '';
};

export const ProfilePage: React.FC<ProfilePageProps> = ({ id, onBack }) => {
  const userInfo = useAppStore(s => s.userInfo);
  const themePreference = useAppStore(s => s.themePreference);
  const setThemePreference = useAppStore(s => s.setThemePreference);
  const name = userInfo?.user_name ?? '';
  const role = roleLabel(userInfo);

  const themeOptions: Array<{ label: string; value: ThemePreference }> = [
    { label: 'Светлая', value: 'light' },
    { label: 'Тёмная', value: 'dark' },
    { label: 'Системная', value: 'system' },
  ];

  return (
    <Panel id={id}>
      <PanelHeader before={<PanelHeaderBack onClick={onBack} />}>
        Профиль
      </PanelHeader>

      {/* Аватар + имя + роль */}
      <Div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 24, paddingBottom: 8 }}>
        <Avatar
          size={96}
          src={userInfo?.avatar || undefined}
          fallbackIcon={
            <span style={{ fontSize: 32, fontWeight: 600 }}>
              {initialsOf(name)}
            </span>
          }
          objectPosition="center top"
        />
        <Text weight="2" style={{ marginTop: 12, fontSize: 18, textAlign: 'center' }}>
          {name}
        </Text>
        {role && (
          <Caption style={{ color: 'var(--vkui--color_text_secondary)', marginTop: 4 }}>
            {role}
          </Caption>
        )}
      </Div>

      {/* Тема оформления */}
      <Group header={<Header size="s">Тема</Header>}>
        <Div>
          <SegmentedControl
            size="l"
            value={themePreference}
            onChange={(value) => setThemePreference(value as ThemePreference)}
            options={themeOptions.map(o => ({ label: o.label, value: o.value }))}
          />
        </Div>
      </Group>

      {/* Выход: реальная навигация, чтобы Odoo закрыл сессию серверно */}
      <Div style={{ paddingTop: 24 }}>
        <Button
          mode="primary"
          appearance="negative"
          size="l"
          stretched
          onClick={() => { window.location.href = '/rost_max/logout'; }}
        >
          Выйти
        </Button>
      </Div>
    </Panel>
  );
};
