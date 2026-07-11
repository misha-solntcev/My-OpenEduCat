import React from 'react';
import { Flex, Typography, Panel, Button, Spinner } from '@maxhub/max-ui';
import { apiGet } from '../api';

interface DashboardPageProps {
  onNavigate: (to: string) => void;
  isAdmin?: boolean;
  isTeacher?: boolean;
  userName?: string;
  globalDate: string;
  onDateChange: (date: string) => void;
}

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

// Мягкие тени — глубина без «грязи» на экране
const cardShadow = '0 4px 12px rgba(0, 0, 0, 0.03), 0 1px 2px rgba(0, 0, 0, 0.04)';

const baseCardStyle: React.CSSProperties = {
  backgroundColor: 'var(--background-surface-card)',
  borderRadius: '12px',
  padding: '16px',
  border: '1px solid var(--border-neutral-subtle)',
  boxShadow: cardShadow,
  width: '100%',
  boxSizing: 'border-box',
};

interface MetricCardProps {
  icon: string;
  label: string;
  value: React.ReactNode;
  borderColor: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ icon, label, value, borderColor }) => (
  <div style={{
    flex: 1,
    backgroundColor: 'var(--background-surface-card)',
    borderRadius: '12px',
    padding: '16px 12px',
    border: '1px solid var(--border-neutral-subtle)',
    borderLeft: `4px solid ${borderColor}`,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',     // центр по горизонтали
    justifyContent: 'center', // центр по вертикали
    textAlign: 'center',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.01), 0 1px 2px rgba(0, 0, 0, 0.02)',
    boxSizing: 'border-box',
    minWidth: 0,
    gap: '6px',
  }}>
    <Flex align="center" gap={8}>
      <span style={{ fontSize: '18px' }}>{icon}</span>
      <Typography.Label variant="small-strong" style={{ color: 'var(--text-muted)', fontWeight: 500 }}>
        {label}
      </Typography.Label>
    </Flex>
    <Typography.Title variant="small-strong" style={{ margin: 0, fontWeight: 800, color: 'var(--text-default)' }}>
      {value}
    </Typography.Title>
  </div>
);

// Цвета левых акцентов (по позиции карточки в сетке 2x2)
const BLUE = '#007aff';
const RED = '#ff3b30';
const GREEN = '#34c759';
const PURPLE = '#5856d6';

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigate,
  isAdmin = false,
  isTeacher = false,
  userName = '',
  globalDate,
  onDateChange,
}) => {
  const role: 'admin' | 'teacher' | 'student' = isAdmin ? 'admin' : isTeacher ? 'teacher' : 'student';
  const statusText = isAdmin ? 'Администратор школы' : isTeacher ? 'Преподаватель' : 'Ученик';

  // Инициалы для аватара (напр. "МС" из "Миша Солнцев")
  const initials = (userName || (isAdmin ? 'ЗА' : isTeacher ? 'ПР' : 'УЧ'))
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('');

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
      {/* 1. Профиль-карточка (вместо заголовка-роли) */}
      <Flex align="center" gap={12} style={baseCardStyle}>
        <div style={{
          width: 44,
          height: 44,
          borderRadius: '50%',
          backgroundColor: '#007aff',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: '16px',
          flexShrink: 0,
        }}>
          {initials}
        </div>
        <Flex direction="column" gap={2} style={{ minWidth: 0 }}>
          <Typography.Title variant="small-strong" style={{ margin: 0, fontWeight: 700, color: 'var(--text-default)' }}>
            {userName || (isAdmin ? 'Завуч' : isTeacher ? 'Преподаватель' : 'Ученик')}
          </Typography.Title>
          <Typography.Label variant="small-strong" style={{ color: 'var(--text-muted)', fontWeight: 500 }}>
            {statusText}
          </Typography.Label>
        </Flex>
      </Flex>

      {loading && (
        <Flex align="center" justify="center" style={{ padding: '48px 0' }}>
          <Spinner />
        </Flex>
      )}

      {!loading && data && (
        <>
          {/* 2. Баннер демо-режима (летние каникулы / выходной) */}
          {data.is_fallback && (
            <div style={{ backgroundColor: 'var(--background-warning-subtle, #fffbe6)', padding: '10px 14px', borderRadius: '12px', border: '1px solid var(--border-warning-subtle, #ffe58f)', display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '16px' }}>🏖️</span>
              <Typography.Body variant="small" style={{ color: 'var(--text-warning, #d46b08)', fontWeight: 500, lineHeight: '1.4' }}>
                Летние каникулы. Показываем архивные данные за последний учебный день: <strong>{data.fallback_date}</strong>
              </Typography.Body>
            </div>
          )}

          {/* 3. Компактный селектор даты */}
          <Flex align="center" gap={10} style={{ ...baseCardStyle, padding: '10px 14px' }}>
            <span style={{ fontSize: '18px' }}>📅</span>
            <input
              type="date"
              value={globalDate}
              onChange={e => onDateChange(e.target.value)}
              style={{
                flex: 1,
                border: 'none',
                backgroundColor: 'transparent',
                color: 'var(--text-default)',
                fontSize: '15px',
                fontWeight: 600,
                outline: 'none',
                fontFamily: 'inherit',
              }}
            />
          </Flex>

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
            <Panel style={{ padding: '14px', borderRadius: '12px', border: '1px solid var(--border-neutral-subtle)', boxShadow: cardShadow }}>
              <Button
                stretched
                style={{ height: '40px', fontSize: '13px', fontWeight: 600 }}
                onClick={() => onNavigate('/rost_max/modules')}
              >
                📢 Объявление
              </Button>
            </Panel>
          )}

          {/* 6. Выход — полноширинная красная кнопка */}
          <Button
            onClick={() => { window.location.href = '/rost_max/logout'; }}
            style={{
              width: '100%',
              height: '42px',
              borderRadius: '10px',
              backgroundColor: 'rgba(255, 59, 48, 0.08)',
              color: '#ff3b30',
              border: 'none',
              fontWeight: 600,
              fontSize: '13px',
              marginTop: '16px',
            }}
          >
            🚪 Выйти из аккаунта
          </Button>
        </>
      )}
    </Flex>
  );
};
