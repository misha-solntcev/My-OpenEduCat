// Материалы задания (вложения учителя): прикрепление + список.
// Общий компонент: вкладка «Мои ДЗ» (feed.tsx) и журнал урока
// (TopicHomeworkCard). Требует существующий op.assignment — API работает
// по assignment_id; кнопка показывается только когда он есть.
// Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { Button } from '@vkontakte/vkui';
import { Icon28AttachOutline } from '@vkontakte/icons';
import { apiGet, apiPost, fileToBase64 } from '@/shared/lib/api';
import type { HomeworkAttachment } from '@/shared/lib/types';

export const MaterialsEditor: React.FC<{ assignmentId: number }> = ({ assignmentId }) => {
  const [materials, setMaterials] = React.useState<HomeworkAttachment[] | null>(null);
  const [busy, setBusy] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const load = React.useCallback(async () => {
    try {
      const res = await apiGet<{ materials: HomeworkAttachment[] }>(
        `/rost_max/api/homework/${assignmentId}/materials`);
      setMaterials(res.materials || []);
    } catch {
      setMaterials([]);
    }
  }, [assignmentId]);

  React.useEffect(() => { load(); }, [load]);

  const addFiles = async (list: FileList | null) => {
    if (!list || list.length === 0) return;
    const MAX_MB = 10;
    const payload = [];
    for (const f of Array.from(list)) {
      const goodType = f.type.startsWith('image/') || f.type === 'application/pdf';
      if (goodType && f.size <= MAX_MB * 1024 * 1024) {
        try {
          payload.push({ filename: f.name, mimetype: f.type, b64: await fileToBase64(f) });
        } catch { /* пропускаем нечитаемый файл */ }
      }
    }
    if (payload.length === 0) return;
    setBusy(true);
    try {
      const res = await apiPost<{ materials?: HomeworkAttachment[] }>(
        `/rost_max/api/homework/${assignmentId}/materials`,
        { files: payload });
      if (res.materials) setMaterials(res.materials);
    } catch { /* оставляем прежний список */ }
    setBusy(false);
  };

  return (
    <div onClick={e => e.stopPropagation()} style={{ marginTop: 6 }}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        multiple
        style={{ display: 'none' }}
        onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
      />
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <Button
          size="s"
          mode="tertiary"
          loading={busy}
          before={<Icon28AttachOutline width={18} height={18} />}
          onClick={() => fileInputRef.current?.click()}
        >
          Материалы
        </Button>
        {materials && materials.length > 0 && materials.map(a => (
          <a
            key={a.url}
            href={a.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: 'var(--vkui--color_text_accent)',
              textDecoration: 'none',
              fontSize: 12,
            }}
          >
            {a.name}
          </a>
        ))}
      </div>
    </div>
  );
};
