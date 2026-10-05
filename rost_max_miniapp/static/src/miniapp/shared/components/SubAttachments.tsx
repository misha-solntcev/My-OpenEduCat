// Вложения сданной работы ученика (очередь проверки и лента учителя).
//
// Раньше здесь был свой рендерер со своим размером 96×96 — из-за него
// превью в миниаппе были разного размера (MaterialsEditor 56, здесь 96).
// Теперь это тонкая обёртка над AttachmentGrid: размер, скругление,
// просмотрщик и забитая ссылка — всё в общем компоненте.
//
// Само разделение на фото/не-фото и правило «файлы не скрываем» — тоже
// в AttachmentGrid, здесь только передача вложений сдачи в него.
import React from 'react';
import { AttachmentGrid } from '@/shared/components/AttachmentGrid';
import type { HomeworkAttachment } from '@/shared/lib/types';

export const SubAttachments: React.FC<{ attachments: HomeworkAttachment[] }> = ({
  attachments,
}) => <AttachmentGrid files={attachments} />;
