// Материалы задания (вложения учителя): прикрепление + превью.
// Общий компонент: вкладка «Мои ДЗ» (feed.tsx) и журнал урока
// (TopicHomeworkCard). Требует существующий op.assignment — API работает
// по assignment_id.
// Оформление — как в мессенджерах: файлы не ссылками, а плитками с
// превью (фото — миниатюра, pdf — иконка с именем), тап открывает
// полноэкранный просмотр с листанием. Кнопку «Материалы» убрали:
// прикрепление идёт скрепкой ВНУТРИ поля ввода ДЗ, здесь только
// результат — что прикреплено.
// Стили: VKUI токены + vkitokens (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { Box, Flex, Text } from '@vkontakte/vkui';
import { Icon16Cancel, Icon28AttachOutline, Icon28DocumentOutline } from '@vkontakte/icons';
import { apiGet, apiPost, fileToBase64 } from '@/shared/lib/api';
import { useToast } from '@/shared/components/Toast';
import { AttachmentThumb, AttachmentViewer } from '@/shared/components/AttachmentGrid';
import type { HomeworkAttachment } from '@/shared/lib/types';


export const MaterialsEditor: React.FC<{
  assignmentId: number;
  /** Показывать свою кнопку прикрепления. Нужна там, где поля ввода ДЗ
   *  нет (лента «Мои ДЗ», экран задания) — прикреплять нечем. В журнале
   *  урока выключаем: скрепка живёт внутри поля ввода ДЗ, вторая была бы
   *  дублем (и раньше выглядела как отдельная строка «Материалы»). */
  showAttachButton?: boolean;
  /** Задание снесено целиком (удалили последний файл фоточного ДЗ) — пора
   *  перечитать урок, иначе в карточке останутся прежние текст и превью. */
  onAssignmentRemoved?: () => void;
  /** Режим просмотра (карточка ДЗ у ученика/родителя): те же миниатюры и
   *  тап-просмотр, но без крестиков, кнопки и запроса в API. */
  readOnly?: boolean;
  /** Готовые вложения (уже пришли в ленте) — не ходим в /materials. */
  initialMaterials?: HomeworkAttachment[];
}> = ({
  assignmentId, showAttachButton = true, onAssignmentRemoved,
  readOnly = false, initialMaterials,
}) => {
  const addToast = useToast();
  const [materials, setMaterials] = React.useState<HomeworkAttachment[] | null>(null);
  const [busy, setBusy] = React.useState(false);
  // индекс открытой во весь экран плитки, null — просмотр закрыт
  const [viewer, setViewer] = React.useState<number | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const load = React.useCallback(async () => {
    // Готовые вложения передали с лентой — запрос не нужен.
    if (initialMaterials) {
      setMaterials(initialMaterials);
      return;
    }
    try {
      const res = await apiGet<{ materials?: HomeworkAttachment[]; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/materials`);
      if (res.error) {
        addToast(res.error, 'error');
        return;
      }
      setMaterials(res.materials || []);
    } catch {
      setMaterials([]);
      addToast('Не удалось загрузить материалы', 'error');
    }
  }, [assignmentId, addToast, initialMaterials]);

  React.useEffect(() => { load(); }, [load]);

  const addFiles = async (list: FileList | null) => {
    if (!list || list.length === 0) return;
    const MAX_MB = 10;
    const skipped: string[] = [];
    const payload = [];
    for (const f of Array.from(list)) {
      const goodType = f.type.startsWith('image/') || f.type === 'application/pdf';
      if (goodType && f.size <= MAX_MB * 1024 * 1024) {
        try {
          payload.push({ filename: f.name, mimetype: f.type, b64: await fileToBase64(f) });
        } catch { /* пропускаем нечитаемый файл */ }
      } else {
        skipped.push(f.name);
      }
    }
    if (skipped.length > 0) {
      addToast(`Пропущены (не фото/pdf или больше 10 МБ): ${skipped.join(', ')}`, 'error');
    }
    if (payload.length === 0) return;
    setBusy(true);
    try {
      // append: сервер дописывает к текущему набору, поэтому ранее
      // загруженные файлы не пропадают (см. _hw_store_attachments).
      const res = await apiPost<{ success?: boolean; materials?: HomeworkAttachment[]; error?: string }>(
        `/rost_max/api/homework/${assignmentId}/materials`,
        { files: payload });
      if (res.error) {
        addToast(res.error, 'error');
      } else {
        setMaterials(res.materials || []);
      }
    } catch {
      addToast('Не удалось прикрепить материалы', 'error');
    }
    setBusy(false);
  };

  // Ссылка для <img>/<a> должна быть абсолютной: токен-роут отдаёт файл,
  // а относительный путь внутри <img> на WebView MAX не всегда резолвится.
  const absUrl = (url: string) =>
    url.startsWith('http') ? url : window.location.origin + url;

  const images = (materials || []).filter(m => (m.mimetype || '').startsWith('image/'));
  const docs = (materials || []).filter(m => !(m.mimetype || '').startsWith('image/'));

  const viewerItem = viewer != null ? (materials || [])[viewer] : null;

  // Удаление ошибочно загруженного файла. Подтверждаем: файлы не вернуть,
  // а на телефоне легко промахнуться по крестику рядом с миниатюрой.
  const removeFile = async (a: HomeworkAttachment) => {
    if (a.id == null) {
      addToast('Не удалось определить файл', 'error');
      return;
    }
    if (!window.confirm(`Удалить файл «${a.name}»?`)) return;
    setBusy(true);
    try {
      const res = await apiPost<{
        success?: boolean; materials?: HomeworkAttachment[]; error?: string;
        // Задание снесено целиком (последний файл фоточного ДЗ) — вызывающий
        // обязан перечитать урок, иначе превью и текст останутся прежними.
        assignment_removed?: boolean;
      }>(`/rost_max/api/homework/${assignmentId}/materials/delete`, {
        attachment_id: a.id,
      });
      if (res.error) {
        addToast(res.error, 'error');
      } else {
        setMaterials(res.materials || []);
        // Просмотр открыт на удалённом файле — закрываем.
        setViewer(null);
        if (res.assignment_removed && onAssignmentRemoved) {
          onAssignmentRemoved();
        }
      }
    } catch {
      addToast('Не удалось удалить файл', 'error');
    }
    setBusy(false);
  };

  return (
    <div onClick={e => e.stopPropagation()} style={{ marginTop: 8 }}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        multiple
        style={{ display: 'none' }}
        onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
      />

      {showAttachButton && (
        <button
          type="button"
          onClick={e => { e.stopPropagation(); fileInputRef.current?.click(); }}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: 'none', border: 0, padding: 0,
            color: 'var(--vkui--color_text_accent)',
            fontSize: 13, marginBottom: materials && materials.length > 0 ? 8 : 0,
          }}
        >
          <Icon28AttachOutline width={18} height={18} />
          {busy ? 'Загружаем…' : 'Прикрепить фото или файл'}
        </button>
      )}

      {/* Фото — сетка миниатюр, как в Telegram. Плитка кликабельна:
          открывает полноэкранный просмотр. */}
      {images.length > 0 && (
        <Flex style={{ flexWrap: 'wrap', gap: 8, marginBottom: docs.length ? 8 : 0 }}>
          {images.map(a => {
            const idx = (materials || []).findIndex(m => m.url === a.url);
            return (
              <Box
                key={a.url}
                onClick={() => setViewer(idx)}
                style={{ position: 'relative', borderRadius: 10, overflow: 'hidden' }}
              >
                <AttachmentThumb url={absUrl(a.url)} alt={a.name} />
                {/* Крестик поверх миниатюры — как в мессенджерах. Тап по
                    крестику не открывает просмотр: stopPropagation.
                    У ученика вложения только для просмотра — крестика
                    нет, это чужой учительский файл. */}
                {!readOnly && (
                  <button
                    type="button"
                    aria-label={`Удалить ${a.name}`}
                    onClick={e => { e.stopPropagation(); removeFile(a); }}
                    style={{
                      position: 'absolute', top: 2, right: 2,
                      width: 22, height: 22, padding: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      borderRadius: '50%',
                      border: 0, cursor: 'pointer',
                      background: 'rgba(0,0,0,0.55)',
                      color: '#fff',
                    }}
                  >
                    <Icon16Cancel width={14} height={14} />
                  </button>
                )}
              </Box>
            );
          })}
        </Flex>
      )}

      {/* Не-фото (pdf и прочее) — плитка с иконкой и именем, тап открывает
          файл. Имя обрезается, чтобы длинное не разносило вёрстку. */}
      {docs.map(a => (
        <Box
          key={a.url}
          onClick={() => window.open(absUrl(a.url), '_blank', 'noopener')}
          style={{ marginTop: 4 }}
        >
          <Flex
            align="center"
            gap={10}
            style={{
              padding: '6px 10px', borderRadius: 10,
              background: 'var(--vkui--color_background_secondary)',
            }}
          >
            <Icon28DocumentOutline width={20} height={20} />
            <Text
              style={{
                fontSize: 13, flexGrow: 1, minWidth: 0,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
            >
              {a.name}
            </Text>
            {!readOnly && (
              <button
                type="button"
                aria-label={`Удалить ${a.name}`}
                onClick={e => { e.stopPropagation(); removeFile(a); }}
                style={{
                  width: 24, height: 24, padding: 0, flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  borderRadius: '50%', border: 0, cursor: 'pointer',
                  background: 'transparent',
                  color: 'var(--vkui--color_icon_secondary)',
                }}
              >
                <Icon16Cancel width={16} height={16} />
              </button>
            )}
          </Flex>
        </Box>
      ))}

      {/* Полноэкранный просмотр: счётчик «N из M», тап — закрыть. Только
          картинки: pdf проще открыть во внешней вкладке (см. docs выше). */}
      {viewerItem && (viewerItem.mimetype || '').startsWith('image/') && (
        <AttachmentViewer
          url={absUrl(viewerItem.url)}
          alt={viewerItem.name}
          caption={[
            images.length > 1
              ? `${(materials || []).filter(m => (m.mimetype || '').startsWith('image/'))
                  .findIndex(m => m.url === viewerItem.url) + 1} из ${images.length}`
              : null,
            'Тап — закрыть',
          ].filter(Boolean).join(' · ')}
          onClose={() => setViewer(null)}
        />
      )}
    </div>
  );
};
