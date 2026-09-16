/**
 * Вкладка «Оценки» учителя/админа — заглушка (итерация в работе).
 * Ученик/родитель видит полноценные SubjectsPage — переключение в App.tsx.
 */
import React from 'react';
import { Panel, Placeholder, Caption } from '@vkontakte/vkui';
import { Icon56SchoolOutline } from '@vkontakte/icons';

export const TeacherGradesPage: React.FC<{ id: string }> = ({ id }) => (
  <Panel id={id}>
    <Placeholder
      icon={<Icon56SchoolOutline />}
      title="Страница в разработке"
    >
      <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
        Экран оценок для учителя появится позже.
      </Caption>
    </Placeholder>
  </Panel>
);
