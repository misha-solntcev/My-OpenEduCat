/**
 * Список ДЗ ученика: каждая запись — отдельная карточка (мокап
 * homework-stitch-variant.html). Используется на главной (лента дня) и
 * на вкладке «Задания».
 *
 * Стили: VKUI токены, никаких кастомных css-классов.
 */
import React from 'react';
import { Caption, Div, Input, Button, Card as VkCard, Text, Box, Flex } from '@vkontakte/vkui';
import { Icon28AttachOutline, Icon28ClockOutline, Icon28DocumentOutline, Icon16Cancel } from '@vkontakte/icons';
import { SubjectAvatar } from './SubjectIcon';
import { MaterialsEditor } from '@/shared/components/MaterialsEditor';
import { AttachField, HW_MAX_HEIGHT } from '@/shared/components/AttachField';
import { fileToBase64 } from '@/shared/lib/api';
import { gradeTone } from './JournalButton';
import type { HomeworkItem } from '@/shared/lib/types';

const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

/** Фото или нет — тем же правилом, что принимает бэкенд (image/* + pdf). */
const isImage = (f: File): boolean => (f.type || '').startsWith('image/');

export const fmtDue = (due: string): string => {
  if (!due) return '';
  const d = new Date(due);
  if (isNaN(d.getTime())) return due;
  const hh = d.getHours();
  const mm = d.getMinutes();
  const time = (hh || mm) ? ` к ${hh}:${String(mm).padStart(2, '0')}` : '';
  return `до ${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}${time}`;
};

/** Дата выдачи «12 сен» (issued_at из grading_assignment.issued_date). */
export const fmtIssued = (iso: string): string => {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return `${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}`;
};

/** Дата сдачи «вчера/сегодня в 19:40» либо «12 сен». */
const fmtSubmitted = (iso: string): string => {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const now = new Date();
  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  const yest = new Date(now); yest.setDate(now.getDate() - 1);
  const day = sameDay(d, now) ? 'сегодня'
    : sameDay(d, yest) ? 'вчера'
      : `${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}`;
  return `${day} в ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

const HW_STATE_LABEL: Record<string, string> = {
  submit: 'На проверке',
  accept: 'Принято',
  change: 'На доработке',
  reject: 'Отклонено',
};

/** Янтарная плашка статуса «на доработке» (у Counter в VKUI 8 нет
 *  жёлтого appearance; светлого warning-тинта тоже нет — заливка
 *  background_warning, как у оценки-3 в журнале). */
const AmberChip: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{
    minWidth: 28, height: 28, borderRadius: 7,
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    paddingInline: 8, fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap',
    background: 'var(--vkui--color_background_warning)',
    border: '1px solid var(--vkui--color_icon_warning)',
    color: 'var(--vkui--color_text_primary)',
  }}>
    {children}
  </span>
);

/** Чип-планка срока справа сверху карточки. Текст — text_primary
 *  (адаптивный); цвет несёт фон-тинт. */
const DueChip: React.FC<{ due: string; overdue?: boolean }> = ({ due, overdue }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center', gap: 4,
    fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap',
    padding: '4px 8px', borderRadius: 8,
    color: 'var(--vkui--color_text_primary)',
    background: overdue ? 'var(--vkui--color_background_negative_tint)'
      : 'var(--vkui--color_background_accent_tint)',
  }}>
    <Icon28ClockOutline width={14} height={14} />
    {fmtDue(due)}
  </span>
);

/** Превью ЛОКАЛЬНОГО файла ученика (ещё не отправлен на сервер), поэтому
 *  через object URL. Фото рисуется миниатюрой, pdf — плиткой с иконкой, как
 *  в MaterialsEditor. Ссылку живёт компонент, снимок — при размонтировании. */
const LocalThumb: React.FC<{ file: File }> = ({ file }) => {
  const isImg = isImage(file);
  const [url, setUrl] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (!isImg) return;
    const u = URL.createObjectURL(file);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [file, isImg]);
  if (!isImg) {
    return (
      <Flex
        align="center"
        gap={6}
        style={{
          padding: '6px 10px', borderRadius: 10, background: 'var(--vkui--color_background_secondary)',
        }}
      >
        <Icon28DocumentOutline width={18} height={18} />
        <Text style={{
          fontSize: 13, maxWidth: 120, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {file.name}
        </Text>
      </Flex>
    );
  }
  return (
    <img
      src={url || undefined}
      alt={file.name}
      style={{ width: 56, height: 56, objectFit: 'cover', display: 'block' }}
    />
  );
};

/** Одна карточка-задание с раскрытием и формой сдачи. */
export const HomeworkRowItem: React.FC<{
  h: HomeworkItem;
  canSubmit?: boolean;
  onSubmit?: (id: number, answer: string, files: { filename: string; mimetype: string; b64: string }[]) => Promise<string | null>;
  onUpdated?: () => void;
}> = ({ h, canSubmit, onSubmit, onUpdated }) => {
  const [expanded, setExpanded] = React.useState(false);
  const [answer, setAnswer] = React.useState('');
  const [files, setFiles] = React.useState<File[]>([]);
  const [busy, setBusy] = React.useState(false);
  // Индекс выбранного для просмотра файла, null — просмотр закрыт.
  const [viewerIndex, setViewerIndex] = React.useState<number | null>(null);
  // Полноэкранный просмотр: URL создаётся ОДИН раз на файл и отзывается
  // при смене/размонтировании — иначе object URL течёт на каждом рендере.
  const [viewerUrl, setViewerUrl] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (viewerIndex === null || !files[viewerIndex]) {
      setViewerUrl(null);
      return;
    }
    const u = URL.createObjectURL(files[viewerIndex]);
    setViewerUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [viewerIndex, files]);

  const open = () => {
    setExpanded(prev => !prev);
    setFiles([]);
    setAnswer(h.state === 'none' || h.state === 'change' ? (h.answer || '') : '');
  };

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    // Лимиты бэкенда: 5 файлов, 10 МБ, фото/pdf.
    const MAX_MB = 10;
    const ok: File[] = [];
    for (const f of Array.from(list)) {
      const goodType = f.type.startsWith('image/') || f.type === 'application/pdf';
      if (goodType && f.size <= MAX_MB * 1024 * 1024) ok.push(f);
    }
    setFiles(prev => [...prev, ...ok].slice(0, 5));
  };

  const send = async () => {
    if (!onSubmit) return;
    setBusy(true);
    const payload = [];
    for (const f of files) {
      try {
        payload.push({ filename: f.name, mimetype: f.type, b64: await fileToBase64(f) });
      } catch {
        setBusy(false);
        return;
      }
    }
    const err = await onSubmit(h.id, answer.trim(), payload);
    setBusy(false);
    if (err === null) {
      setExpanded(false);
      setFiles([]);
      onUpdated?.();
    }
  };

  const label = HW_STATE_LABEL[h.state];

  // Правая верхняя плашка: у принятых — большой бейдж-оценка (как в
  // мокапе «Биология — 5»), у «на доработке» — янтарная плашка, у
  // остальных — статус/срок.
  let right: React.ReactNode;
  if (h.state === 'accept') {
    const tone = gradeTone(h.mark);
    right = (
      <span style={{ display: 'inline-flex', gap: 4, flexShrink: 0 }}>
        {h.mark && <span style={{
          minWidth: 36, height: 36, borderRadius: 9,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18, fontWeight: 700, lineHeight: '24px',
          background: tone.bg, border: `1px solid ${tone.border}`, color: tone.text,
        }}>{h.mark}</span>}
        {h.mark_2 && <span style={{
          minWidth: 36, height: 36, borderRadius: 9,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18, fontWeight: 700, lineHeight: '24px',
          background: gradeTone(h.mark_2).bg,
          border: `1px solid ${gradeTone(h.mark_2).border}`,
          color: gradeTone(h.mark_2).text,
        }}>{h.mark_2}</span>}
        {!h.mark && !h.mark_2 && <span style={{
          minWidth: 36, height: 36, borderRadius: 9,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18, fontWeight: 700, lineHeight: '24px',
          background: tone.bg, border: `1px solid ${tone.border}`, color: tone.text,
        }}>—</span>}
      </span>
    );
  } else if (h.state === 'change') {
    right = <AmberChip>{label}</AmberChip>;
  } else if (h.state === 'submit') {
    right = (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap',
        padding: '4px 8px', borderRadius: 8,
        color: 'var(--vkui--color_text_secondary)',
        background: 'var(--vkui--color_background_secondary)',
      }}>
        <Icon28ClockOutline width={14} height={14} />
        На проверке
      </span>
    );
  } else {
    right = <DueChip due={h.due} overdue={h.overdue} />;
  }

  // Точка-статус слева: зелёная — сдано/принято, янтарная — на доработке,
  // синяя — новое/не сдано, красная — только просрочено.
  const dotColor = h.state === 'accept' || h.state === 'submit'
    ? 'var(--vkui--color_background_positive)'
    : h.state === 'change'
      ? 'var(--vkui--color_icon_warning)'
      : h.overdue
        ? 'var(--vkui--color_background_negative)'
        : 'var(--vkui--color_background_accent)';

  return (
    <VkCard mode="shadow" style={{ marginBottom: 8, overflow: 'hidden' }}>
      {/* Шапка карточки: аватар предмета + название + плашка. Тап по карточке раскрывает содержимое. */}
      <div
        onClick={open}
        style={{ cursor: 'pointer', padding: '12px 12px 0', display: 'flex', alignItems: 'flex-start', gap: 10 }}
      >
        <SubjectAvatar subject={h.subject} color={h.subject_color} />
        <span style={{
          width: 10, height: 10, borderRadius: '50%', flexShrink: 0, marginTop: 6,
          background: dotColor,
        }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text weight="2" style={{ fontSize: 16, lineHeight: '22px' }}>
            {h.subject}
          </Text>
          {h.topic && (
            <Caption style={{
              color: 'var(--vkui--color_text_secondary)',
              display: 'block', marginTop: 1, whiteSpace: 'nowrap',
              overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {h.topic}
            </Caption>
          )}
          <Caption style={{
            color: 'var(--vkui--color_text_secondary)',
            display: 'block', marginTop: 1, whiteSpace: 'nowrap',
            overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {h.state === 'submit' || h.state === 'accept'
              ? `Отправлено ${h.submitted_at ? fmtSubmitted(h.submitted_at) : ''}${h.late ? ' · с опозданием' : ''}`
              : (h.issued_at ? `Выдано ${fmtIssued(h.issued_at)}` : '')}
          </Caption>
        </div>
        {right}
      </div>

      {/* Текст задания и содержимое */}
      <div style={{ padding: '8px 12px 12px 32px' }}>
        <Text style={{ color: 'var(--vkui--color_text_primary)', display: 'block', whiteSpace: 'pre-wrap' }}>
          {h.task}
        </Text>

        {expanded && (
          <div style={{ marginTop: 8 }}>
            {h.state === 'change' && h.teacher_note && (
              <div style={{
                display: 'flex', gap: 8, alignItems: 'flex-start',
                background: 'var(--vkui--color_background_warning)',
                borderRadius: 10, padding: '8px 10px', marginBottom: 8,
              }}>
                <Icon28AttachOutline width={16} height={16} style={{
                  color: 'var(--vkui--color_icon_warning)', flexShrink: 0, marginTop: 2,
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Caption weight="2" style={{
                    color: 'var(--vkui--color_text_primary)',
                    display: 'block', fontSize: 11, marginBottom: 2,
                  }}>
                    Комментарий учителя
                  </Caption>
                  <Text style={{
                    color: 'var(--vkui--color_text_primary)',
                    display: 'block', whiteSpace: 'pre-wrap',
                  }}>
                    {h.teacher_note}
                  </Text>
                </div>
              </div>
            )}

            {h.answer_required && h.answer && h.state !== 'change' && (
              <div style={{ marginBottom: 8 }}>
                <Caption style={{
                  color: 'var(--vkui--color_text_secondary)',
                  display: 'block', marginBottom: 2,
                }}>
                  Ваш ответ:
                </Caption>
                <Text style={{ color: 'var(--vkui--color_text_primary)', display: 'block', whiteSpace: 'pre-wrap' }}>
                  {h.answer}
                </Text>
              </div>
            )}

            {/* Материалы учителя — те же миниатюры с тап-просмотром, что в
                его карточке (MaterialsEditor в режиме readOnly). Раньше были
                ссылки-чипы с именем файла: имя не скажет ученику, что там на
                фото, а открывать надо было в новой вкладке. */}
            {h.materials.length > 0 && (
              <MaterialsEditor
                key={`mats:${h.id}`}
                assignmentId={h.id}
                showAttachButton={false}
                readOnly
                initialMaterials={h.materials}
              />
            )}

            {canSubmit && (h.state === 'none' || h.state === 'draft' || h.state === 'change' || h.state === 'reject') ? (
              <div style={{ marginTop: 8 }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,application/pdf"
                  multiple
                  style={{ display: 'none' }}
                  onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
                />
                {/* Ответ со скрепкой: общий компонент AttachField, ровно
                    как в журнале учителя. Отдельная кнопка «Прикрепить» под
                    полем была дублем: слово «Прикрепить» не нужно, значок
                    всё говорит, а поле оставалось на всю ширину карточки. */}
                <AttachField
                  value={answer}
                  onChange={setAnswer}
                  placeholder={h.answer_required ? 'Ваш ответ' : 'Ответ или просто прикрепите фото'}
                  ariaLabel="Ответ на задание"
                  attachProps={{
                    onClick: (e: React.MouseEvent) => {
                      /* stopPropagation: карточка раскрывается по тапу. */
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    },
                    }}
                    maxHeight={HW_MAX_HEIGHT}
                    />
                {/* Кнопка сдачи — по центру и своей ширины, не stretched:
                    растянутая на всю карточку она читалась как «поле формы»,
                    а действие здесь одно и очевидное. */}
                <Flex justify="center" style={{ marginTop: 8 }}>
                  <Button
                    size="l"
                    mode="primary"
                    loading={busy}
                    disabled={h.answer_required && !answer.trim()}
                    onClick={send}
                  >
                    {(h.answer_required || files.length > 0) ? 'Сдать' : 'Сделано'}
                  </Button>
                </Flex>
                {files.length > 0 && (
                  /* Выбранные файлы — локальные (File), до отправки на сервере
                     их нет, поэтому превью строим через object URL, а не
                     берём из MaterialsEditor. Вид тот же, что у учителя:
                     сетка миниатюр, тап — полноэкранный просмотр, крестик
                     убирает файл. */
                  <Flex style={{ flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
                    {files.map((f, i) => (
                      <Box
                        key={`${f.name}-${i}`}
                        style={{ position: 'relative', borderRadius: 10, overflow: 'hidden' }}
                      >
                        <Box
                          onClick={() => {
                            if (isImage(f)) setViewerIndex(i);
                          }}
                          style={{ display: 'block' }}
                        >
                          <LocalThumb file={f} />
                        </Box>
                        <button
                          type="button"
                          aria-label={`Убрать ${f.name}`}
                          onClick={() => setFiles(prev => prev.filter((_, j) => j !== i))}
                          style={{
                            position: 'absolute', top: 2, right: 2,
                            width: 22, height: 22, padding: 0,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            borderRadius: '50%', border: 0, cursor: 'pointer',
                            background: 'rgba(0,0,0,0.55)', color: '#fff',
                          }}
                        >
                          <Icon16Cancel width={14} height={14} />
                        </button>
                      </Box>
                    ))}
                  </Flex>
                )}

                {/* Полноэкранный просмотр выбранного фото, как у учителя. */}
                {viewerIndex !== null && viewerUrl && isImage(files[viewerIndex]) && (
                  <div
                    onClick={() => setViewerIndex(null)}
                    style={{
                      position: 'fixed', inset: 0, zIndex: 1000,
                      background: 'rgba(0,0,0,0.92)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                  >
                    <img
                      src={viewerUrl}
                      alt={files[viewerIndex].name}
                      style={{ maxWidth: '100%', maxHeight: '82%', objectFit: 'contain' }}
                    />
                  </div>
                )}
              </div>
            ) : (
              h.state === 'submit' && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6, marginTop: 8,
                  background: 'var(--vkui--color_background_secondary)',
                  color: 'var(--vkui--color_text_secondary)',
                  fontSize: 11, padding: '6px 8px', borderRadius: 8,
                }}>
                  <Icon28ClockOutline width={14} height={14} />
                  Ожидает проверки учителя
                </div>
              )
            )}
          </div>
        )}

        {h.overdue && (h.state === 'none' || h.state === 'change') && (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 8,
            fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap',
            padding: '4px 8px', borderRadius: 8, alignSelf: 'flex-start',
            color: 'var(--vkui--color_text_primary)',
            background: 'var(--vkui--color_background_negative_tint)',
          }}>
            <Icon28ClockOutline width={14} height={14} />
            Просрочено
          </span>
        )}
      </div>
    </VkCard>
  );
};

/**
 * Каждая запись — отдельная карточка (VkCard mode="shadow").
 * title/afterTitle — заголовок блока вне карточек (у вкладки «Задания»
 * это заголовок группы; у ленты главной — текст + «Все задания →»).
 */
export const HomeworkCardList: React.FC<{
  items: HomeworkItem[];
  title?: React.ReactNode;
  afterTitle?: React.ReactNode;
  canSubmit?: boolean;
  onSubmit?: (id: number, answer: string, files: { filename: string; mimetype: string; b64: string }[]) => Promise<string | null>;
  onUpdated?: () => void;
  max?: number;
}> = ({ items, title, afterTitle, canSubmit, onSubmit, onUpdated, max }) => (
  <div style={{ margin: '0 8px 8px' }}>
    {(title != null || afterTitle != null) && (
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '12px 8px 8px',
      }}>
        {title}
        {afterTitle}
      </div>
    )}
    {items.length === 0 ? (
      <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Заданий нет — можно отдыхать</Caption></Div>
    ) : (
      <>
        {(max != null ? items.slice(0, max) : items).map(h => (
          <HomeworkRowItem
            key={h.id}
            h={h}
            canSubmit={canSubmit}
            onSubmit={onSubmit}
            onUpdated={onUpdated}
          />
        ))}
        {max != null && items.length > max && (
          <Div style={{ paddingTop: 0 }}>
            <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
              Ещё {items.length - max} — на вкладке «Задания»
            </Caption>
          </Div>
        )}
      </>
    )}
  </div>
);
