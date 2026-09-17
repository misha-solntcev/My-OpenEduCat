/**
 * Список ДЗ ученика: каждая запись — отдельная карточка (мокап
 * homework-stitch-variant.html). Используется на главной (лента дня) и
 * на вкладке «Задания».
 *
 * Стили: VKUI токены, никаких кастомных css-классов.
 */
import React from 'react';
import { Caption, Div, Input, Button, Card as VkCard, Text } from '@vkontakte/vkui';
import { Icon28AttachOutline, Icon28ClockOutline } from '@vkontakte/icons';
import { SubjectIcon } from './SubjectIcon';
import { fileToBase64 } from '@/shared/lib/api';
import type { HomeworkItem } from '@/shared/lib/types';

const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

export const fmtDue = (due: string): string => {
  if (!due) return '';
  const d = new Date(due);
  if (isNaN(d.getTime())) return due;
  const hh = d.getHours();
  const mm = d.getMinutes();
  const time = (hh || mm) ? ` к ${hh}:${String(mm).padStart(2, '0')}` : '';
  return `до ${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}${time}`;
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
  submit: 'Сдано',
  accept: 'Принято',
  change: 'На доработке',
  reject: 'Отклонено',
};

/** Тон оценки как в журнале (JournalButton): 5 зелёная, 4 синяя,
 *  3 янтарная (warning — светлого тинта нет в VKUI 8.3.1, берём
 *  заливку background_warning), 2 красная; не задана — «—».
 *  ВАЖНО: текст на тинте — text_primary (адаптивный тёмный/светлый),
 *  НЕ цветной — цветной цвет на своём тинте не читается ни в одной
 *  теме (замечание Миши). Цвет несёт фон+рамка. */
const markTone = (mark: number | null) => {
  if (mark === 5) return {
    bg: 'var(--vkui--color_background_positive_tint)',
    border: 'var(--vkui--color_stroke_positive)',
    text: 'var(--vkui--color_text_primary)',
  };
  if (mark === 4) return {
    bg: 'var(--vkui--color_background_accent_tint)',
    border: 'var(--vkui--color_stroke_accent)',
    text: 'var(--vkui--color_text_primary)',
  };
  if (mark === 3) return {
    bg: 'var(--vkui--color_background_warning)',
    border: 'var(--vkui--color_icon_warning)',
    text: 'var(--vkui--color_text_primary)',
  };
  if (mark === 2) return {
    bg: 'var(--vkui--color_background_negative_tint)',
    border: 'var(--vkui--color_stroke_negative)',
    text: 'var(--vkui--color_text_primary)',
  };
  return {
    bg: 'var(--vkui--color_background_secondary)',
    border: 'var(--vkui--color_separator_primary)',
    text: 'var(--vkui--color_text_secondary)',
  };
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

/** Цветной квадрат-аватар предмета: иконка + пастель по цвету предмета.
 *  ЦВЕТ предмета — Integer op.subject.color (задаётся в интерфейсе).
 *  ПАЛИТРА = стандартная календаря Odoo ($o-colors-complete + mix white
 *  55%), НЕ main.scss (тот — канбан/пикер и даёт другой набор). Календарь
 *  красит o_calendar_color_N: JS getColor(c)=((c-1)%55)+1 в класс N,
 *  sass-цикл делает класс {i-1} из элемента i — значит элемент N+1,
 *  фон = mix(white, элемент N+1, 55%). Проверено по скрину: Алгебра
 *  color=4 -> синяя #a3c4ec. */

/** $o-colors-complete (первичные 1..56), 0-байтный индекс = элемент N+1.
 *  value = пастель mix(white, base, 55%). */
const ODOO_COLORS: { bg: string; color: string }[] = [
  { bg: '#cccccc', color: '#a2a2a2' }, { bg: '#f68c8c', color: '#ee2d2d' }, { bg: '#ecbc8f', color: '#dc8534' }, { bg: '#f2da83', color: '#e8bb1d' }, { bg: '#a3c4ec', color: '#5794dd' }, { bg: '#caa9c1', color: '#9f628f' }, { bg: '#ebbeaa', color: '#db8865' }, { bg: '#96d0cc', color: '#41a9a2' },
  { bg: '#8d9cee', color: '#304be0' }, { bg: '#f68dbf', color: '#ee2f8a' }, { bg: '#a8deaf', color: '#61c36e' }, { bg: '#c6b1f1', color: '#9872e6' }, { bg: '#d09cae', color: '#aa4b6b' }, { bg: '#8ddeba', color: '#30c381' }, { bg: '#c6b393', color: '#97743a' }, { bg: '#fbe484', color: '#f7cd1f' },
  { bg: '#97bcf9', color: '#4285f4' }, { bg: '#c187d0', color: '#8e24aa' }, { bg: '#e87ea7', color: '#d6145f' }, { bg: '#7f9598', color: '#173e43' }, { bg: '#8fc19f', color: '#348f50' }, { bg: '#d09392', color: '#aa3a38' }, { bg: '#b5a29a', color: '#795548' }, { bg: '#a6748e', color: '#5e0231' },
  { bg: '#aef1bc', color: '#6be585' }, { bg: '#c7c7ab', color: '#999966' }, { bg: '#f3e7a9', color: '#e9d362' }, { bg: '#d6acac', color: '#b56969' }, { bg: '#dbdee0', color: '#bdc3c7' }, { bg: '#aac2b2', color: '#649173' }, { bg: '#f373ff', color: '#ea00ff' }, { bg: '#ff7388', color: '#ff0026' },
  { bg: '#bfe373', color: '#8bcc00' }, { bg: '#73dcd3', color: '#00bfaf' }, { bg: '#73adff', color: '#006aff' }, { bg: '#d373dc', color: '#af00bf' }, { bg: '#dc7383', color: '#bf001d' }, { bg: '#dca973', color: '#bf6300' }, { bg: '#c0ff73', color: '#8cff00' }, { bg: '#73f8ff', color: '#00f2ff' },
  { bg: '#739bd5', color: '#004ab3' }, { bg: '#ff73e5', color: '#ff00d0' }, { bg: '#ffce73', color: '#ffa600' }, { bg: '#93e373', color: '#3acc00' }, { bg: '#73d7dc', color: '#00b6bf' }, { bg: '#739aff', color: '#0048ff' }, { bg: '#dcb773', color: '#bf7c00' }, { bg: '#75ff73', color: '#04ff00' },
  { bg: '#73e5ff', color: '#00d0ff' }, { bg: '#7390dc', color: '#0036bf' }, { bg: '#ff73c0', color: '#ff008c' }, { bg: '#73dc9b', color: '#00bf49' }, { bg: '#73c3d5', color: '#0092b3' }, { bg: '#7375ff', color: '#0004ff' }, { bg: '#d573a9', color: '#b20062' }, { bg: '#aac2b2', color: '#649173' },
];

/** Затемнение базового цвета до контраста 3:1 с пастельным фоном. */
const contrastingIconColor = (base: string, bg: string): string => {
  const rgb = (hex: string) => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  const luminance = (channels: number[]) => {
    const [r, g, b] = channels.map(channel => {
      const s = channel / 255;
      return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const channels = rgb(base);
  const background = luminance(rgb(bg));
  for (let step = 0; step <= 100; step++) {
    const darkened = channels.map(channel => Math.round(channel * (1 - step / 100)));
    const foreground = luminance(darkened);
    const contrast = (Math.max(background, foreground) + 0.05)
      / (Math.min(background, foreground) + 0.05);
    if (contrast >= 3) return `#${darkened.map(channel => channel.toString(16).padStart(2, '0')).join('')}`;
  }
  return '#000000';
};

// Палитра постоянна: считаем контраст один раз, не при рендере карточки.
const SUBJECT_COLORS = ODOO_COLORS.map(({ bg, color }) => ({
  bg, color: contrastingIconColor(color, bg),
}));

/** Цвет предмета (Integer op.subject.color) -> {пастель, контрастная иконка}.
 *  getColor(c)=((c-1)%55)+1 = номер класса N; sass генерит класс {i-1}
 *  из элемента i -> элемент N+1; массив 0-индексирован (элемент 1 ->
 *  index 0) -> index = N = ((c-1)%55)+1. Проверено: Алгебра color=4 ->
 *  N=4 -> элемент 5 #5794dd -> синяя. 0/без значения — нейтральный.
 *  Иконка — оттенок предмета с контрастом не ниже 3:1 к фону. */
const subjectColor = (color: number): { bg: string; color: string } => {
  if (!color) return { bg: 'var(--vkui--color_background_secondary)', color: 'var(--vkui--color_text_secondary)' };
  const index = ((color - 1) % 55) + 1; // 1..55, валидный индекс массива
  return SUBJECT_COLORS[index];
};

/** Квадрат-аватар предмета 38px в шапке карточки: пастель из БД + иконка по названию. */
const SubjectAvatar: React.FC<{ subject: string; color?: number }> = ({ subject, color }) => {
  const c = subjectColor(color || 0);
  return (
    <span style={{
      width: 38, height: 38, borderRadius: 10, flexShrink: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: c.bg, color: c.color,
    }}>
      <SubjectIcon subject={subject} />
    </span>
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
  const fileInputRef = React.useRef<HTMLInputElement>(null);

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
    const tone = markTone(h.mark);
    right = (
      <span style={{
        minWidth: 36, height: 36, borderRadius: 9, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18, fontWeight: 700, lineHeight: '24px',
        background: tone.bg, border: `1px solid ${tone.border}`, color: tone.text,
      }}>
        {h.mark || '—'}
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
          <Caption style={{
            color: 'var(--vkui--color_text_secondary)',
            display: 'block', marginTop: 1, whiteSpace: 'nowrap',
            overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {h.state === 'submit' || h.state === 'accept'
              ? `Отправлено ${h.submitted_at ? fmtSubmitted(h.submitted_at) : ''}${h.late ? ' · с опозданием' : ''}`
              : (h.task.length > 60 ? h.task.slice(0, 60) + '…' : h.task)}
          </Caption>
        </div>
        {right}
      </div>

      {/* Текст задания и содержимое */}
      <div style={{ padding: '8px 12px 12px 32px' }}>
        <Caption style={{ color: 'var(--vkui--color_text_primary)', display: 'block', whiteSpace: 'pre-wrap' }}>
          {h.task}
        </Caption>

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
                  <Caption style={{
                    color: 'var(--vkui--color_text_primary)',
                    display: 'block', whiteSpace: 'pre-wrap',
                  }}>
                    {h.teacher_note}
                  </Caption>
                </div>
              </div>
            )}

            {h.answer_required && h.answer && h.state !== 'change' && (
              <Caption style={{
                color: 'var(--vkui--color_text_secondary)',
                display: 'block', marginBottom: 8, whiteSpace: 'pre-wrap',
              }}>
                Ваш ответ: {h.answer}
              </Caption>
            )}

            {h.materials.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                {h.materials.map(a => (
                  <a
                    key={a.url}
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 5,
                      background: 'var(--vkui--color_background_secondary)',
                      color: 'var(--vkui--color_text_secondary)',
                      fontSize: 11, padding: '4px 8px', borderRadius: 8,
                      textDecoration: 'none', whiteSpace: 'nowrap',
                      maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}
                  >
                    <Icon28AttachOutline width={14} height={14} style={{ color: 'var(--vkui--color_text_accent)', flexShrink: 0 }} />
                    {a.name}
                  </a>
                ))}
              </div>
            )}

            {canSubmit && (h.state === 'none' || h.state === 'draft' || h.state === 'change' || h.state === 'reject') ? (
              <div style={{ marginTop: 8 }}>
                {h.answer_required && (
                  <Input
                    value={answer}
                    onChange={e => setAnswer(e.target.value)}
                    placeholder="Ваш ответ"
                    aria-label="Ответ на задание"
                    style={{ marginBottom: 8 }}
                  />
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,application/pdf"
                  multiple
                  style={{ display: 'none' }}
                  onChange={e => { addFiles(e.target.files); e.target.value = ''; }}
                />
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <Button
                    size="s"
                    mode="tertiary"
                    before={<Icon28AttachOutline width={20} height={20} />}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Прикрепить
                  </Button>
                  <Button
                    size="s"
                    stretched
                    loading={busy}
                    disabled={h.answer_required && !answer.trim()}
                    onClick={send}
                  >
                    {(h.answer_required || files.length > 0) ? 'Сдать' : 'Сделано'}
                  </Button>
                </div>
                {files.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    {files.map((f, i) => (
                      <Caption
                        key={`${f.name}-${i}`}
                        style={{ color: 'var(--vkui--color_text_secondary)', display: 'block' }}
                      >
                        {f.name} ({Math.round(f.size / 1024)} КБ)
                      </Caption>
                    ))}
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
