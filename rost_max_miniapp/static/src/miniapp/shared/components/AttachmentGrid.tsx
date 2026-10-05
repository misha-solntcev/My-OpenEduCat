// Превью вложений ДЗ — один компонент для всех мест.
//
// ДО ЗАЧЕМ. Размер плитки раньше был захардкожен в трёх компонентах, и
// все три разошлись: MaterialsEditor 56×56, HomeworkCardList 56×56 без
// скругления, SubAttachments 96×96. Миша: «Превью почему-то разного
// размера». Теперь размер задаётся здесь один раз, а остальные места
// его не дублируют.
//
// ЧТО ВНУТРИ:
//   AttachmentThumb  — одна плитка-превью (файл → превью или иконка);
//   AttachmentGrid  — сетка плиток с тапом и полноэкранным просмотром;
//   AttachmentViewer — полноэкранный просмотр одного файла.
//
// РАЗМЕР. Плитка — AttachmentThumbSize (112). Это заметно больше прежних
// 56: фотографию работы с телефона надо рассмотреть, а не угадать. От
// прежнего 96 в SubAttachments тоже больше — та плитка была в списке
// ответов, где сетка может оказаться узкой.
//
// Формат: квадрат по THUMB, objectFit cover — миниатюра всегда
// одинаковая, поэтому сетка не «прыгает» на разных пропорциях.
// Полный просмотр — contain, файл показывается целиком, без обрезки.
//
// Битая ссылка (токен истёк, файл удалён) даёт плитку с иконкой, а не
// пустоту: файл всё равно можно открыть по тапу.
//
// Не-картинки (pdf, doc, zip) превью не имеют — их Grid рисует ссылкой
// с иконкой. Ничего не скрываем и не схлопываем: сколько файлов, столько
// и плиток.
//
// Стили: VKUI токены (--vkui--*), никаких кастомных css-классов.
import React from 'react';
import { Box, Caption, Flex, Image } from '@vkontakte/vkui';
import { Icon28AttachOutline, Icon28DocumentOutline } from '@vkontakte/icons';
import type { HomeworkAttachment } from '@/shared/lib/types';

/** Сторона плитки-превью, px. Единственное место, где размер задаётся. */
export const AttachmentThumbSize = 112;
/** Радиус скругления плитки, px. */
const RADIUS = 10;
/** Зазор между плитками, px. */
const GAP = 8;

/** Ссылка токен-роута относительная, а внутри <img> на WebView MAX
 *  относительный путь не всегда резолвится — делаем абсолютной. */
export const absAttachmentUrl = (url: string): string =>
  url.startsWith('http') ? url : window.location.origin + url;

export const isImageAttachment = (a: HomeworkAttachment): boolean =>
  (a.mimetype || '').startsWith('image/');

/** Одна плитка. url может быть и токен-ссылкой, и blob: из File. */
export const AttachmentThumb: React.FC<{
  url: string;
  alt: string;
  isImage?: boolean;
  size?: number;
}> = ({ url, alt, isImage = true, size = AttachmentThumbSize }) => {
  const [broken, setBroken] = React.useState(false);
  const box: React.CSSProperties = {
    width: size, height: size, borderRadius: RADIUS,
    background: 'var(--vkui--color_background_secondary)',
  };
  if (!isImage) {
    return (
      <Flex
        align="center"
        gap={6}
        style={{
          ...box, padding: '6px 10px', boxSizing: 'border-box',
        }}
      >
        <Icon28DocumentOutline width={18} height={18} />
        <Caption style={{ fontSize: 13, maxWidth: size - 40, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {alt}
        </Caption>
      </Flex>
    );
  }
  if (broken) {
    return (
      <div style={{ ...box, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon28AttachOutline width={24} height={24} />
      </div>
    );
  }
  return (
    <Image
      src={url}
      alt={alt}
      onError={() => setBroken(true)}
      style={{ ...box, objectFit: 'cover', display: 'block' }}
    />
  );
};

/** Полноэкранный просмотр одного файла. onClose обязателен. */
export const AttachmentViewer: React.FC<{
  url: string;
  alt: string;
  /** Подпись «2 из 5» под фото, если нужна листание. */
  caption?: string;
  onClose: () => void;
}> = ({ url, alt, caption, onClose }) => (
  <Box
    onClick={onClose}
    style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.92)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexDirection: 'column',
    }}
  >
    <img
      src={url}
      alt={alt}
      style={{ maxWidth: '100%', maxHeight: '82%', objectFit: 'contain' }}
    />
    {caption && (
      <Caption style={{ color: '#fff', marginTop: 12, fontSize: 13 }}>{caption}</Caption>
    )}
  </Box>
);

/** Сетка превью: фото плитками, остальные файлы ссылками. Тап — просмотр.
 *  onOpen — если передан, фото кликабельны (иначе открываются в новой
 *  вкладке, как это делает MaterialsEditor для неинтерактивных мест). */
export const AttachmentGrid: React.FC<{
  files: { url: string; name: string; mimetype?: string }[];
  onOpen?: (index: number) => void;
  /** Ссылка на файл для открытия, когда onOpen не передан. */
  size?: number;
}> = ({ files, onOpen, size = AttachmentThumbSize }) => {
  const [viewer, setViewer] = React.useState<number | null>(null);
  if (!files || files.length === 0) return null;
  const url = (i: number) => absAttachmentUrl(files[i].url);
  const isImg = (i: number) => (files[i].mimetype || '').startsWith('image/');

  const open = (i: number) => {
    if (onOpen) return onOpen(i);
    if (isImg(i)) return setViewer(i);
    window.open(url(i), '_blank', 'noopener');
  };

  return (
    <>
      <Flex style={{ flexWrap: 'wrap', gap: GAP, marginBottom: 6 }}>
        {files.map((f, i) =>
          isImg(i) ? (
            <Box
              key={`${f.url}-${i}`}
              onClick={() => open(i)}
              style={{ borderRadius: RADIUS, overflow: 'hidden' }}
            >
              <AttachmentThumb url={url(i)} alt={f.name} size={size} />
            </Box>
          ) : (
            <a
              key={`${f.url}-${i}`}
              href={url(i)}
              target="_blank"
              rel="noopener noreferrer"
              onClick={e => { if (onOpen) { e.preventDefault(); open(i); } }}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                color: 'var(--vkui--color_text_accent)',
                textDecoration: 'none', paddingBlock: 3,
              }}
            >
              <Icon28AttachOutline width={16} height={16} />
              <Caption>{f.name}</Caption>
            </a>
          ),
        )}
      </Flex>
      {viewer != null && (
        <AttachmentViewer
          url={url(viewer)}
          alt={files[viewer].name}
          onClose={() => setViewer(null)}
        />
      )}
    </>
  );
};