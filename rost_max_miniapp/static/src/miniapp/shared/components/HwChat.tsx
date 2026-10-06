/**
 * Чат сдачи ДЗ — вариант C (design/hw-chat-variants.html).
 *
 * Лента одной сдачи: пузыри сообщений (ученик/учитель), системные записи
 * («Отправлено на проверку») по центру, вложения внутри пузыря строками
 * с именем и размером, тап — полноэкранный просмотр с кнопкой «Скачать».
 * Композитор снизу — текст + скрепка (те же лимиты, что у сдач).
 *
 * Данные: GET/POST /rost_max/api/homework/submission/<id>/messages.
 * Хранилище — штатный mail.thread строки сдачи (см. контроллер).
 *
 * Мокап C: время одним элементом на группу (последнее из подряд идущих
 * сообщений одного автора), день — разделителем «Сегодня, 18:42».
 */
import React from 'react';
import { Box, Caption, Flex, IconButton, Text } from '@vkontakte/vkui';
import { Icon24Send, Icon28AttachOutline, Icon28DocumentOutline } from '@vkontakte/icons';
import { apiGet, apiPost, fileToBase64 } from '@/shared/lib/api';
import { AttachField, HW_MAX_HEIGHT, type AttachProps } from '@/shared/components/AttachField';
import { absAttachmentUrl, AttachmentThumb, AttachmentViewer, isImageAttachment } from '@/shared/components/AttachmentGrid';
import type { HomeworkFeedItem } from '@/shared/lib/types';

/** 1234567 -> «1,2 МБ» / «345 КБ». */
const fmtSize = (bytes?: number): string => {
  if (!bytes) return '';
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} МБ`;
  }
  return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
};

const fmtTime = (d: Date): string =>
  `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;

const sameDay = (a: Date, b: Date): boolean =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

/** «Сегодня, 18:42» / «Вчера, 09:10» / «12 окт, 19:00». */
const fmtDayLabel = (d: Date): string => {
  const now = new Date();
  if (sameDay(d, now)) return 'Сегодня';
  const yest = new Date(now);
  yest.setDate(now.getDate() - 1);
  if (sameDay(d, yest)) return 'Вчера';
  const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  return `${d.getDate()} ${months[d.getMonth()]}`;
};

/** Плитка ЛОКАЛЬНОГО файла (ещё не отправлен): фото — object URL миниатюрой,
 *  pdf — плиткой с именем. Крестик сверху убирает файл из набора. Тот же
 * AttachmentThumb, что у загруженных вложений — размер/скругление общие. */
const HwPickThumb: React.FC<{ file: File; onRemove: () => void }> = ({ file, onRemove }) => {
  const isImg = (file.type || '').startsWith('image/');
  const [url, setUrl] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (!isImg) return;
    const u = URL.createObjectURL(file);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [file, isImg]);
  return (
    <Box style={{ position: 'relative', borderRadius: 10, overflow: 'hidden' }}>
      <AttachmentThumb url={url || ''} alt={file.name} isImage={isImg} />
      <span
        role="button"
        tabIndex={0}
        aria-label={`Убрать ${file.name}`}
        onClick={onRemove}
        onKeyDown={e => { if (e.key === 'Enter') onRemove(); }}
        style={{
          position: 'absolute', top: 2, right: 2, width: 20, height: 20,
          borderRadius: '50%', background: 'rgba(0,0,0,0.55)', color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, lineHeight: '20px', cursor: 'pointer',
        }}
      >
        ✕
      </span>
    </Box>
  );
};

type FeedMsg = {
  item: HomeworkFeedItem;
  time: Date | null;
};

/** Числовая дата из 'YYYY-MM-DD HH:MM:SS' (сервер шлёт UTC-наивную строку;
 *  для группировки по дням достаточно локального парса). */
const parseDate = (iso: string): Date | null => {
  if (!iso) return null;
  const d = new Date(iso.includes('T') ? iso : iso.replace(' ', 'T') + 'Z');
  return isNaN(d.getTime()) ? null : d;
};

export const HwChat: React.FC<{
  subId: number;
  /** Тап по карточке-родителю может гонять expand — глушим клики. */
  canPost: boolean;
  /** aria-label поля ввода. */
  ariaLabel?: string;
  placeholder?: string;
}> = ({ subId, canPost, ariaLabel = 'Сообщение', placeholder = 'Сообщение…' }) => {
  const [feed, setFeed] = React.useState<HomeworkFeedItem[] | null>(null);
  const [error, setError] = React.useState(false);
  // Проп — начальное значение; сервер решает сам (родитель читать может,
  // писать нет), его слово авторитетнее.
  const [canPostS, setCanPostS] = React.useState(canPost);
  const [text, setText] = React.useState('');
  const [files, setFiles] = React.useState<File[]>([]);
  const [busy, setBusy] = React.useState(false);
  const [viewer, setViewer] = React.useState<{ url: string; name: string } | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const listRef = React.useRef<HTMLDivElement | null>(null);

  const load = React.useCallback(async () => {
    try {
      const res = await apiGet<{ feed?: HomeworkFeedItem[]; can_post?: boolean; error?: string }>(
        `/rost_max/api/homework/submission/${subId}/messages`);
      if (res.error) {
        setError(true);
        setFeed([]);
      } else {
        setFeed(res.feed || []);
        setError(false);
        if (typeof res.can_post === 'boolean') setCanPostS(res.can_post);
      }
    } catch {
      setError(true);
      setFeed([]);
    }
  }, [subId]);

  React.useEffect(() => { load(); }, [load]);

  // Новое сообщение -> автоскролл вниз (как в мессенджерах).
  React.useEffect(() => {
    const el = listRef.current;
    if (el && feed && feed.length) el.scrollTop = el.scrollHeight;
  }, [feed]);

  const send = async () => {
    const t = text.trim();
    if (busy || (!t && files.length === 0)) return;
    setBusy(true);
    try {
      // await ВНУТРИ map: Promise.all по объектам с Promise-полем не ждёт
      // fileToBase64 — в JSON уходил Promise без b64 и файл молча терялся
      // (сервер пропускает записи без b64).
      const payload = await Promise.all(files.map(async f => ({
        filename: f.name,
        mimetype: f.type,
        b64: await fileToBase64(f),
      })));
      const res = await apiPost<{ success?: boolean; feed?: HomeworkFeedItem[]; error?: string }>(
        `/rost_max/api/homework/submission/${subId}/messages`,
        { text: t, files: payload });
      if (res.error) {
        setError(true);
      } else {
        setText('');
        setFiles([]);
        setFeed(res.feed || []);
      }
    } catch {
      setError(true);
    }
    setBusy(false);
  };

  const attachProps: AttachProps = {
    disabled: busy,
    onClick: (e: React.MouseEvent) => {
      e.stopPropagation();
      fileInputRef.current?.click();
    },
  };

  // Группировка подряд идущих msg одного side: время — у последнего.
  const rows: FeedMsg[] = React.useMemo(() => {
    if (!feed) return [];
    return feed.map((item, i) => {
      if (item.kind !== 'msg') return { item, time: parseDate(item.date) };
      const next = feed[i + 1];
      const isLastOfGroup = !next || next.kind !== 'msg' || next.side !== item.side;
      return { item, time: isLastOfGroup ? parseDate(item.date) : null };
    });
  }, [feed]);

  const bubbleStyle = (out: boolean): React.CSSProperties => ({
    maxWidth: '78%',
    padding: '8px 12px',
    borderRadius: 14,
    borderTopLeftRadius: out ? undefined : 4,
    borderTopRightRadius: out ? 4 : undefined,
    background: out
      ? 'var(--vkui--color_background_accent_tint)'
      : 'var(--vkui--color_background_secondary)',
    marginLeft: out ? 'auto' : undefined,
    marginRight: out ? undefined : 'auto',
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div
        ref={listRef}
        style={{
          display: 'flex', flexDirection: 'column', gap: 6,
          maxHeight: 320, overflowY: 'auto',
        }}
        onClick={e => e.stopPropagation()}
      >
        {feed === null && !error && (
          <Caption style={{ padding: '8px 0', color: 'var(--vkui--color_text_secondary)' }}>
            Загрузка…
          </Caption>
        )}
        {error && (
          <Caption style={{ padding: '8px 0', color: 'var(--vkui--color_text_secondary)' }}>
            Не удалось загрузить переписку
          </Caption>
        )}
        {feed && feed.length === 0 && !error && (
          <Caption style={{ padding: '8px 0', color: 'var(--vkui--color_text_secondary)' }}>
            Переписки ещё нет
          </Caption>
        )}
        {rows.map(({ item, time }, i) => {
          const prev = rows[i - 1]?.item;
          const d = time || parseDate(item.date);
          const prevD = parseDate(prev?.date || '');
          const newDay = item.kind === 'msg' && d && (!prev || !prevD || !sameDay(d, prevD));
          return (
            <React.Fragment key={`${item.kind}-${item.date}-${i}`}>
              {item.kind === 'msg' && newDay && d && (
                <Caption style={{
                  alignSelf: 'center', color: 'var(--vkui--color_text_secondary)',
                  fontSize: 11, padding: '2px 0',
                }}>
                  {fmtDayLabel(d)}
                </Caption>
              )}
              {item.kind === 'event' ? (
                <Caption style={{
                  alignSelf: 'center', color: 'var(--vkui--color_text_secondary)',
                  fontSize: 11, background: 'var(--vkui--color_background_secondary)',
                  borderRadius: 10, padding: '3px 10px',
                  marginTop: i > 0 ? 2 : 0,
                }}>
                  {item.text}
                </Caption>
              ) : (
                <div style={{ ...bubbleStyle(item.side === 'out') }}>
                  {item.text && (
                    <Text style={{
                      display: 'block', fontSize: 14, lineHeight: '19px',
                      whiteSpace: 'pre-wrap', overflowWrap: 'anywhere',
                    }}>
                      {item.text}
                    </Text>
                  )}
                  {(item.attachments || []).map((a, j) => {
                    const url = absAttachmentUrl(a.url);
                    const img = isImageAttachment(a);
                    return (
                      <div
                        key={`${a.url}-${j}`}
                        role="button"
                        tabIndex={0}
                        onClick={e => { e.stopPropagation(); setViewer({ url, name: a.name }); }}
                        onKeyDown={e => {
                          if (e.key === 'Enter') { e.stopPropagation(); setViewer({ url, name: a.name }); }
                        }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          marginTop: 6, cursor: 'pointer', minWidth: 0,
                        }}
                      >
                        {img ? (
                          <img
                            src={url}
                            alt={a.name}
                            style={{
                              width: 44, height: 44, borderRadius: 8,
                              objectFit: 'cover', flexShrink: 0,
                              background: 'var(--vkui--color_background_secondary)',
                            }}
                          />
                        ) : (
                          <span style={{
                            width: 44, height: 44, borderRadius: 8, flexShrink: 0,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            background: 'var(--vkui--color_background_content)',
                          }}>
                            <Icon28DocumentOutline width={22} height={22} />
                          </span>
                        )}
                        <span style={{
                          minWidth: 0, fontSize: 12, lineHeight: '16px',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}>
                          {a.name}
                          {a.size ? (
                            <span style={{
                              color: 'var(--vkui--color_text_secondary)',
                            }}>{` · ${fmtSize(a.size)}`}</span>
                          ) : null}
                        </span>
                        <Icon28AttachOutline
                          width={16} height={16}
                          style={{
                            color: 'var(--vkui--color_icon_secondary)',
                            flexShrink: 0, marginLeft: 'auto',
                          }}
                        />
                      </div>
                    );
                  })}
                  {time && (
                    <Caption style={{
                      display: 'block', textAlign: 'right', marginTop: 2,
                      color: 'var(--vkui--color_text_secondary)', fontSize: 10,
                    }}>
                      {fmtTime(time)}
                    </Caption>
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {viewer && (
        <AttachmentViewer
          url={viewer.url}
          alt={viewer.name}
          onClose={() => setViewer(null)}
        />
      )}

      {canPostS && (
        <div style={{ marginTop: 2 }} onClick={e => e.stopPropagation()}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,application/pdf"
            multiple
            style={{ display: 'none' }}
            onChange={e => {
              const picked = Array.from(e.target.files || []);
              setFiles(prev => [...prev, ...picked].slice(0, 5));
              e.target.value = '';
            }}
          />
          <AttachField
            value={text}
            onChange={setText}
            placeholder={placeholder}
            ariaLabel={ariaLabel}
            attachProps={attachProps}
            maxHeight={HW_MAX_HEIGHT}
          />
          {files.length > 0 && (
            /* Выбранные файлы — превью, как у сдач в HomeworkCardList:
               фото миниатюрой (object URL), pdf — плиткой с иконкой и
               именем. Тап по крестику убирает файл из набора. */
            <Flex style={{ flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
              {files.map((f, i) => (
                <HwPickThumb
                  key={`${f.name}-${i}`}
                  file={f}
                  onRemove={() => setFiles(prev => prev.filter((_, j) => j !== i))}
                />
              ))}
            </Flex>
          )}
        </div>
      )}
      {canPostS && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }} onClick={e => e.stopPropagation()}>
          <IconButton
            label="Отправить сообщение"
            disabled={busy || (!text.trim() && files.length === 0)}
            onClick={send}
          >
            <Icon24Send />
          </IconButton>
        </div>
      )}
      {!canPostS && (
        <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
          Писать в переписке могут только ученик и учитель
        </Caption>
      )}
    </div>
  );
};