// Вложения сданной работы ученика.
//
// Раньше в двух местах (очередь проверки ReviewQueue и лента feed.tsx)
// вложения рисовались одинаково: скрепка + имя файла, ссылка. Из-за
// этого учитель картинку ученика видел как ссылку, которую надо сначала
// скачать, хотя ученик и учитель загружали фото одним способом и в
// MaterialsEditor превью уже было.
//
// Здесь картинки рисуются плиткой-превью с тапом — как в MaterialsEditor,
// то есть одинаково для всех ролей. Не-картинки остаются ссылками: PDF
// и архивы превью не имеют, им место в списке файлов.
//
// Файлы не скрываем и не схлопываем: сколько ученик приложил, столько
// плиток. Порядок и число берём из ответа API без правок.
//
// Стили: VKUI токены (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { Image } from '@vkontakte/vkui';
import { Icon28AttachOutline } from '@vkontakte/icons';
import { Caption } from '@vkontakte/vkui';
import type { HomeworkAttachment } from '@/shared/lib/types';

/** Ссылка токен-роута относительная, а внутри <img> на WebView MAX
 *  относительный путь не всегда резолвится — делаем абсолютной. */
const absUrl = (url: string) =>
  url.startsWith('http') ? url : window.location.origin + url;

const isImage = (a: HomeworkAttachment) => (a.mimetype || '').startsWith('image/');

/** Превью одной картинки. Битая ссылка не ломает список: показываем
 *  плитку с иконкой документа, файл всё равно можно открыть по таку. */
const Tile: React.FC<{ a: HomeworkAttachment }> = ({ a }) => {
  const [broken, setBroken] = React.useState(false);
  const box: React.CSSProperties = {
    width: 96, height: 96, borderRadius: 10,
    background: 'var(--vkui--color_background_secondary)',
  };
  if (broken) {
    return (
      <div style={{ ...box, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon28AttachOutline width={24} height={24} />
      </div>
    );
  }
  return (
    <Image
      src={absUrl(a.url)}
      alt={a.name}
      onError={() => setBroken(true)}
      style={{ ...box, objectFit: 'cover', display: 'block' }}
    />
  );
};

export const SubAttachments: React.FC<{
  attachments: HomeworkAttachment[];
  /** Размер плитки превью; по умолчанию 96 — как у MaterialsEditor. */
  size?: number;
}> = ({ attachments, size = 96 }) => {
  if (!attachments || attachments.length === 0) return null;
  const images = attachments.filter(isImage);
  const docs = attachments.filter(a => !isImage(a));
  return (
    <div style={{ marginTop: 6 }}>
      {images.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {images.map(a => (
            <a
              key={a.url}
              href={absUrl(a.url)}
              target="_blank"
              rel="noopener noreferrer"
              style={{ display: 'block', width: size, height: size }}
            >
              <Tile a={a} />
            </a>
          ))}
        </div>
      )}
      {docs.map(a => (
        <a
          key={a.url}
          href={absUrl(a.url)}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            color: 'var(--vkui--color_text_accent)',
            textDecoration: 'none', paddingBlock: 3,
          }}
        >
          <Icon28AttachOutline width={16} height={16} />
          <Caption>{a.name}</Caption>
        </a>
      ))}
    </div>
  );
};