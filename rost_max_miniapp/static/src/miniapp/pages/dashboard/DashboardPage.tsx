import React from 'react';
import { Panel, PanelHeader, Flex, Text, Spinner, Avatar, Button, SimpleGrid, SimpleCell, Group, DateInput } from '@vkontakte/vkui';
import { apiGet } from '@/shared/lib/api';
import { initialsOf } from '@/shared/lib/initials';
import { useAppStore, selectGlobalDate, setGlobalDate } from '@/shared/lib/store';
import { useToast } from '@/shared/components/Toast';
import type { DashboardResponse, NextLesson, DashboardMetrics } from '@/shared/lib/types';
import { Tile } from '@/pages/dashboard/components/Tile';

export const DashboardPage: React.FC<{ id: string; onNavigate: (to: string) => void }> = ({ id, onNavigate }) => {
  const userInfo = useAppStore(s => s.userInfo);
  const globalDate = useAppStore(selectGlobalDate);
  const addToast = useToast();

  const handleDateChange = (date: Date | null) => {
    if (date) {
      setGlobalDate(date.toISOString().split('T')[0]);
    }
  };

  const isAdmin = userInfo?.is_admin ?? false;
  const isTeacher = userInfo?.is_teacher ?? false;
  const userName = userInfo?.user_name ?? '';
  const statusText = isAdmin ? 'Администратор' : isTeacher ? 'Преподаватель' : 'Ученик';

  // Fallback-имя, когда userInfo.user_name пуст (анимная/незагруженная сессия)
  const roleFallback = isAdmin ? 'Завуч' : isTeacher ? 'Преподаватель' : 'Ученик';

  // Инициалы для аватара — единый формат (одна буква) для всех ролей
  const initials = initialsOf(userName || roleFallback);

  const [data, setData] = React.useState<DashboardResponse | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<DashboardResponse>(`/rost_max/api/dashboard_info?date=${globalDate}`)
      .then(d => { if (!cancelled) setData(d); })
      .catch((err: unknown) => {
        if (!cancelled) {
          setData(null);
          console.error('Dashboard load failed:', err);
          addToast('Не удалось загрузить данные', 'error');
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [globalDate, addToast]);

  const m: DashboardMetrics = data?.metrics ?? {};

  return (
    <Panel id={id}>
      <PanelHeader>Главная</PanelHeader>
      <Flex direction="column" align="stretch" gap={16}>
      {/* 1. Профиль — нативная ячейка (Avatar + имя + роль) */}
      <Group header="Профиль">
              <SimpleCell
                before={
                  <Avatar size={40} initials={initials} gradientColor="blue" />
                }
                title={userName || roleFallback}
                subtitle={statusText}
              />
            </Group>

      {loading && (
        <Flex align="center" justify="center" padding="xl">
          <Spinner />
        </Flex>
      )}

      {!loading && data && (
        <>
          {/* 3. Компактный селектор даты */}
          <DateInput
            mode="plain"
            value={new Date(globalDate)}
            onChange={handleDateChange}
            size="s"
            placeholder={globalDate}
          />

          {/* 4. Инфографика 2x2 (SimpleGrid + Tile метрик) */}
          <SimpleGrid cols={2} gap={12}>
            {isAdmin ? (
              <>
                <Tile icon="🏫" label="Сегодня уроков" value={m.active_lessons ?? 0} />
                <Tile icon="⚠️" label="Нет журнала" value={m.unfilled_sheets ?? 0} />
                <Tile icon="👥" label="Посещаемость" value={`${m.attendance_pct ?? 0}%`} />
                <Tile icon="🧑‍🎓" label="Учеников" value={m.total_students ?? 0} />
              </>
            ) : isTeacher ? (
              <>
                <Tile icon="🏫" label="Мои уроки" value={m.total_lessons ?? 0} />
                <Tile icon="✅" label="Проведено" value={m.completed_lessons ?? 0} />
                <Tile icon="👥" label="Посещаемость" value={`${m.attendance_pct ?? 0}%`} />
                <Tile icon="✍️" label="Выставлено оценок" value={m.graded_count ?? 0} />
              </>
            ) : (
              <>
                <Tile icon="⭐" label="Средний балл" value={(m.gpa ?? 0).toFixed(2)} />
                <Tile icon="📝" label="Домашних задач" value={m.pending_homework ?? 0} />
                <Tile icon="👥" label="Моя посещаемость" value={`${m.attendance_pct ?? 0}%`} />
              </>
            )}
          </SimpleGrid>

          {/* 5. Админ: единственная уникальная кнопка действия */}
          {isAdmin && (
            <Button
              mode="primary"
              appearance="accent"
              stretched
              before="📢"
              onClick={() => onNavigate('/rost_max/modules')}
            >
              Объявление
            </Button>
          )}

          {/* 6. Выход — destructive-кнопка (real navigation: Odoo сбрасывает сессию). */}
          <Flex justify="center" width="100%">
            <Button
              appearance="negative"
              onClick={() => { window.location.href = '/rost_max/logout'; }}
            >
              Выйти
            </Button>
          </Flex>
        </>
      )}
    </Flex>
    </Panel>
  );
};
