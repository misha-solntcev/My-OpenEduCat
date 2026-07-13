import React from 'react';
import { Flex, Typography, Spinner, Avatar, Button, CellList, CellSimple } from '@maxhub/max-ui';
import { apiGet } from '../../shared/lib';
import { initialsOf } from '../../shared/lib';
import { DateJumper } from '../../widgets/date-jumper';
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

interface MetricCardProps {
  icon: string;
  label: string;
  value: React.ReactNode;
  borderColor: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ icon, label, value, borderColor }) => (
  <div style={{
  flex: 1,
  borderLeft: `4px solid ${borderColor}`,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center',
  minWidth: 0,
  gap: '6px',
  }} className="rm-card rm-card--metric">
    <Flex align="center" gap={8}>
      <span style={{ fontSize: '18px' }}>{icon}</span>
      <Typography.Label variant="small-strong" style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
        {label}
      </Typography.Label>
    </Flex>
    <Typography.Title variant="small-strong" style={{ margin: 0, fontWeight: 800, color: 'var(--text-primary)' }}>
      {value}
    </Typography.Title>
  </div>
);

// Цвета левых акцентов (по позиции карточки в сетке 2x2)
const BLUE = 'var(--background-accent-themed)';
const RED = 'var(--background-accent-negative)';
const GREEN = 'var(--background-accent-positive)';
const PURPLE = '#5856d6';

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
          {/* 2. Баннер демо-режима (летние каникулы / выходной) */}
          {data.is_fallback && (
            <div className="rm-card" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '16px', color: 'var(--background-accent-attention-primary)' }}>🏖️</span>
              <Typography.Body variant="small" style={{ color: 'var(--background-accent-attention-primary)', fontWeight: 500, lineHeight: '1.4' }}>
                Летние каникулы. Показываем архивные данные за последний учебный день: <strong>{data.fallback_date}</strong>
              </Typography.Body>
            </div>
          )}

          {/* 3. Компактный селектор даты */}
          <DateJumper value={globalDate} onChange={setGlobalDate} />

          {/* 4. Инфографика 2x2 с левыми акцентами */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', width: '100%' }}>
            {isAdmin ? (
              <>
                <MetricCard icon="🏫" label="Сегодня уроков" value={m.active_lessons ?? 0} borderColor={BLUE} />
                <MetricCard icon="⚠️" label="Нет журнала" value={m.unfilled_sheets ?? 0} borderColor={RED} />
                <MetricCard icon="👥" label="Посещаемость" value={`${m.attendance_pct ?? 0}%`} borderColor={GREEN} />
                <MetricCard icon="🧑‍🎓" label="Учеников" value={m.total_students ?? 0} borderColor={PURPLE} />
              </>
            ) : isTeacher ? (
              <>
                <MetricCard icon="🏫" label="Мои уроки" value={m.total_lessons ?? 0} borderColor={BLUE} />
                <MetricCard icon="✅" label="Проведено" value={m.completed_lessons ?? 0} borderColor={RED} />
                <MetricCard icon="👥" label="Посещаемость" value={`${m.attendance_pct ?? 0}%`} borderColor={GREEN} />
                <MetricCard icon="✍️" label="Выставлено оценок" value={m.graded_count ?? 0} borderColor={PURPLE} />
              </>
            ) : (
              <>
                <MetricCard icon="⭐" label="Средний балл" value={(m.gpa ?? 0).toFixed(2)} borderColor={BLUE} />
                <MetricCard icon="📝" label="Домашних задач" value={m.pending_homework ?? 0} borderColor={RED} />
                <MetricCard icon="👥" label="Моя посещаемость" value={`${m.attendance_pct ?? 0}%`} borderColor={GREEN} />
              </>
            )}
          </div>

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
