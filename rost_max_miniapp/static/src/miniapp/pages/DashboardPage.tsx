import React from 'react';
import { Flex, Spinner, Avatar, Button, SimpleGrid, SimpleCell, Group } from '@vkontakte/vkui';
import { apiGet, initialsOf } from '@/lib';
import { DateJumper } from '@/components/DateJumper';
import { Tile } from '@/components/Tile';
import { useAppStore, selectGlobalDate, setGlobalDate } from '@/lib/store';

interface DashboardData {
  is_admin: boolean;
  is_teacher: boolean;
  is_student: boolean;
  date: string;
  metrics: {
    active_lessons?: number;
    unfilled_sheets?: number;
    attendance_pct?: number;
    total_students?: number;
    pending_substitutes?: number;
    total_lessons?: number;
    completed_lessons?: number;
    graded_count?: number;
    gpa?: number;
    pending_homework?: number;
  };
  next_lesson: {
    id: number;
    subject: string;
    batch: string;
    time: string;
    room: string;
  } | null;
}

export const DashboardPage: React.FC<{ onNavigate: (to: string) => void }> = ({ onNavigate }) => {
  const userInfo = useAppStore(s => s.userInfo);
  const globalDate = useAppStore(selectGlobalDate);
  // setGlobalDate доступен через импорт и используется в DateJumper ниже

  const isAdmin = userInfo?.is_admin ?? false;
  const isTeacher = userInfo?.is_teacher ?? false;
  const userName = userInfo?.user_name ?? '';
  const statusText = isAdmin ? 'Администратор' : isTeacher ? 'Преподаватель' : 'Ученик';

  // Fallback-имя, когда userInfo.user_name пуст (анимная/незагруженная сессия)
  const roleFallback = isAdmin ? 'Завуч' : isTeacher ? 'Преподаватель' : 'Ученик';

  // Инициалы для аватара — единый формат (одна буква) для всех ролей
  const initials = initialsOf(userName || roleFallback);

  const [data, setData] = React.useState<DashboardData | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<DashboardData>(`/rost_max/api/dashboard_info?date=${globalDate}`)
      .then(d => { if (!cancelled) setData(d); })
      .catch(() => { if (!cancelled) setData(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [globalDate]);

  const m = data?.metrics ?? {};

  return (
    <Flex direction="column" align="stretch" gap={16} style={{ width: '100%' }}>
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
        <Flex align="center" justify="center" style={{ padding: '48px 0' }}>
          <Spinner />
        </Flex>
      )}

      {!loading && data && (
        <>
          {/* 3. Компактный селектор даты */}
          <DateJumper value={globalDate} onChange={setGlobalDate} />

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
          <Flex justify="center" style={{ width: '100%' }}>
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
  );
};
