import React from 'react';
import { Flex, Typography, Spinner, Avatar, Button, CellList, CellSimple, Grid } from '@maxhub/max-ui';
import { apiGet } from '../../shared/lib';
import { initialsOf } from '../../shared/lib';
import { DateJumper } from '../../widgets/date-jumper';
import { Card, CardHeader, CardContent } from '../../widgets/card';
import { useAppStore } from '../../app/store';

interface DashboardData {
  is_admin: boolean;
  is_teacher: boolean;
  is_student: boolean;
  date: string;
  is_fallback: boolean;
  fallback_date: string;
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
  const globalDate = useAppStore(s => s.getGlobalDate());
  const setGlobalDate = useAppStore(s => s.setGlobalDate);

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
    <Flex direction="column" gap={16} style={{ width: '100%' }}>
      {/* 1. Профиль — нативная ячейка (Avatar + имя + роль) */}
      <CellList mode="island">
        <CellSimple
          before={(
            <Avatar.Container size={40} form="squircle">
              <Avatar.Text>{initials}</Avatar.Text>
            </Avatar.Container>
          )}
          title={userName || roleFallback}
          subtitle={statusText}
        />
      </CellList>

      {loading && (
        <Flex align="center" justify="center" style={{ padding: '48px 0' }}>
          <Spinner />
        </Flex>
      )}

      {!loading && data && (
        <>
          {/* 2. Баннер демо-режима (летние каникулы / выходной) — нативная ячейка */}
          {data.is_fallback && (
            <CellList mode="island">
              <CellSimple
                before={<span style={{ fontSize: '24px' }}>🏖️</span>}
                title={<Typography.Body variant="small" style={{ color: 'var(--background-accent-attention-primary)', fontWeight: 500, lineHeight: '1.4' }}>Летние каникулы. Показываем архивные данные за последний учебный день: <strong>{data.fallback_date}</strong></Typography.Body>}
              />
            </CellList>
          )}

          {/* 3. Компактный селектор даты */}
          <DateJumper value={globalDate} onChange={setGlobalDate} />

          {/* 4. Инфографика 2x2 (нативный Grid; цветной бордер метрик — позже через Card-вариант) */}
          <Grid cols={2} gap={12}>
            {isAdmin ? (
              <>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>🏫</span>} title="Сегодня уроков" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{m.active_lessons ?? 0}</CardContent>
                </Card>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>⚠️</span>} title="Нет журнала" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{m.unfilled_sheets ?? 0}</CardContent>
                </Card>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>👥</span>} title="Посещаемость" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{`${m.attendance_pct ?? 0}%`}</CardContent>
                </Card>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>🧑‍🎓</span>} title="Учеников" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{m.total_students ?? 0}</CardContent>
                </Card>
              </>
            ) : isTeacher ? (
              <>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>🏫</span>} title="Мои уроки" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{m.total_lessons ?? 0}</CardContent>
                </Card>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>✅</span>} title="Проведено" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{m.completed_lessons ?? 0}</CardContent>
                </Card>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>👥</span>} title="Посещаемость" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{`${m.attendance_pct ?? 0}%`}</CardContent>
                </Card>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>✍️</span>} title="Выставлено оценок" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{m.graded_count ?? 0}</CardContent>
                </Card>
              </>
            ) : (
              <>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>⭐</span>} title="Средний балл" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{(m.gpa ?? 0).toFixed(2)}</CardContent>
                </Card>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>📝</span>} title="Домашних задач" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{m.pending_homework ?? 0}</CardContent>
                </Card>
                <Card>
                  <CardHeader justify="center" media={<span style={{ fontSize: '18px' }}>👥</span>} title="Моя посещаемость" />
                  <CardContent align="center" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>{`${m.attendance_pct ?? 0}%`}</CardContent>
                </Card>
              </>
            )}
          </Grid>

          {/* 5. Админ: единственная уникальная кнопка действия */}
          {isAdmin && (
            <Button
              mode="primary"
              appearance="themed"
              stretched
              iconBefore="📢"
              onClick={() => onNavigate('/rost_max/modules')}
            >
              Объявление
            </Button>
          )}

          {/* 6. Выход — destructive-кнопка (real navigation: Odoo сбрасывает сессию).
              Без stretched — обёртка на всю ширину центрирует кнопку по горизонтали. */}
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
