/**
 * Верхняя строка корневого таба (решение Миши 2026-10-14): аватар
 * «кто смотрит» СЛЕВА — на всех табах в одном углу (на главной он слева
 * в приветствии и не прыгает), тап открывает профиль; справа — слот
 * after под кнопку фильтра (как в «Заданиях» учителя, где иконка уже
 * справа). Слева аватар безопасен: Back есть только на вложенных
 * экранах, где шапки таба нет. Корневые табы без PanelHeader — активный
 * таб виден в таббаре.
 */
import React from 'react';
import { Avatar, Text } from '@vkontakte/vkui';
import { useAppStore } from '@/shared/lib/store';
import { initialsOf } from '@/shared/lib/initials';

export const TabHeader: React.FC<{
  title: string;
  /** Правый слот (кнопка фильтра у staff-ролей). */
  after?: React.ReactNode;
  onOpenProfile?: () => void;
}> = ({ title, after, onOpenProfile }) => {
  const userInfo = useAppStore(s => s.userInfo);
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '12px 16px 6px',
    }}>
      {/* Размеры как в Greeting на главной (аватар 48, инициалы 18,
          заголовок 20) — решение Миши 2026-10-14. */}
      <Avatar
        size={48}
        src={userInfo?.avatar || undefined}
        fallbackIcon={
          <span style={{ fontSize: 18, fontWeight: 600 }}>
            {initialsOf(userInfo?.user_name ?? '')}
          </span>
        }
        objectPosition="center top"
        style={{
          borderRadius: 8, flexShrink: 0,
          cursor: onOpenProfile ? 'pointer' : undefined,
        }}
        onClick={onOpenProfile}
      />
      <Text weight="2" style={{ fontSize: 20, flex: 1, minWidth: 0 }}>
        {title}
      </Text>
      {after}
    </div>
  );
};
