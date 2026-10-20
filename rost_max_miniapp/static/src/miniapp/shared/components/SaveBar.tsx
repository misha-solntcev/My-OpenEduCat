import React from 'react';
import { Box, Button } from '@vkontakte/vkui';

interface SaveBarProps {
  visible: boolean;
  saving: boolean;
  onSave: () => void;
}

/**
 * Плавающая кнопка «Сохранить» — общий каркас экранов с локальным буфером
 * правок (журнал урока, проверка ДЗ). Показывается, пока есть
 * несохранённые изменения (dirty).
 *
 * fixed, а не sticky: sticky прижимает бар к низу СКРОЛЯЩЕГОСЯ контейнера,
 * то есть бар виден только когда доскроллил до конца контента. fixed
 * якорит бар к экрану (на ПК-виде — к корпусу телефона: transform на
 * .desktop-device__screen делает его containing block, см.
 * desktop-frame.css) — бар висит внизу всегда, как в журнале урока.
 * Над таббаром: tabbar fixed height 48px (--vkui_internal--tabbar_height).
 */
export const SaveBar: React.FC<SaveBarProps> = ({ visible, saving, onSave }) => {
  if (!visible) return null;

  return (
    <Box
      position="fixed"
      insetBlockEnd="var(--vkui_internal--tabbar_height, 48px)"
      insetInline={0}
      padding="m"
      paddingInline="l"
      style={{
        borderTop: '1px solid var(--vkui--color_separator_primary)',
        backgroundColor: 'var(--vkui--color_background_content)',
        zIndex: 'var(--vkui--z_index_popout)',
      }}
    >
      <Button
        stretched
        size="l"
        mode="primary"
        appearance="accent"
        loading={saving}
        onClick={onSave}
      >
        Сохранить
      </Button>
    </Box>
  );
};
