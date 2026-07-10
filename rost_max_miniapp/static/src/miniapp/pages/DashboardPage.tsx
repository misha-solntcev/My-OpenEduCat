import React from 'react';
import { CellAction, CellList, Typography, Flex } from '@maxhub/max-ui';

interface DashboardPageProps {
  onNavigate: (to: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const openTimetable = () => {
    onNavigate('/rost_max/timetable');
  };

  return (
    <>
      <CellList>
        <CellAction onClick={openTimetable}>
          <Typography.Body>Расписание занятий</Typography.Body>
        </CellAction>
      </CellList>

      <Flex style={{ justifyContent: 'center', marginTop: '16px', cursor: 'pointer' }}>
        <Typography.Label variant="secondary" size="s" onClick={() => { window.location.href = '/rost_max/logout'; }}>
          Выйти
        </Typography.Label>
      </Flex>
    </>
  );
};