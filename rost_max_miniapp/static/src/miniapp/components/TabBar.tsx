import React from 'react';
import { Tabbar, TabbarItem } from '@vkontakte/vkui';
import { Icon28HomeOutline, Icon28CalendarOutline, Icon28GridLayoutOutline } from '@vkontakte/icons';

interface TabBarProps {
  currentTab?: string;
  onTabChange: (tabId: string) => void;
}

export const TabBar: React.FC<TabBarProps> = ({ currentTab, onTabChange }) => (
  <Tabbar mode="horizontal">
    <TabbarItem
      label="Главная"
      selected={currentTab === 'dashboard'}
      onClick={() => onTabChange('dashboard')}
    >
      <Icon28HomeOutline />
    </TabbarItem>
    <TabbarItem
      label="Расписание"
      selected={currentTab === 'timetable'}
      onClick={() => onTabChange('timetable')}
    >
      <Icon28CalendarOutline />
    </TabbarItem>
    <TabbarItem
      label="Модули"
      selected={currentTab === 'modules'}
      onClick={() => onTabChange('modules')}
    >
      <Icon28GridLayoutOutline />
    </TabbarItem>
  </Tabbar>
);
