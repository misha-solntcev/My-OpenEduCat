/**
 * Список ДЗ ученика с раскрытием и сдачей (ответ + вложения).
 * Используется на главной (лента дня) и на вкладке «Задания».
 *
 * Стили: VKUI токены, никаких кастомных css-классов.
 */
import React from 'react';
import { SimpleCell, Caption, Div, Counter, Input, Button, Card as VkCard } from '@vkontakte/vkui';
import { Icon28AttachOutline } from '@vkontakte/icons';
import { fileToBase64 } from '@/shared/lib/api';
import type { HomeworkItem } from '@/shared/lib/types';

const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

export const fmtDue = (due: string): string => {
  if (!due) return '';
  const d = new Date(due);
  if (isNaN(d.getTime())) return due;
  return `до ${d.getDate()} ${MONTHS[d.getMonth()].slice(0, 3)}`;
};

const HW_STATE_LABEL: Record<string, string> = {
  submit: 'Сдано',
  accept: 'Принято',
  change: 'На доработку',
  reject: 'Отклонено',
};

/** Одна строка-задание с раскрытием и формой сдачи. */
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
  return (
    <div style={{ borderTop: '1px solid var(--vkui--color_background_secondary)' }}>
      <SimpleCell
        onClick={open}
        before={
          <span style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 2,
            background: h.state === 'accept' || h.state === 'submit'
              ? 'var(--vkui--color_background_positive)'
              : 'var(--vkui--color_background_negative)',
          }} />
        }
        after={
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {label && (
              // VKUI 8: цвет — через appearance (mode только
              // primary/contrast/tertiary/inherit).
              <Counter
                mode="primary"
                appearance={h.state === 'accept' ? 'accent-green'
                  : h.state === 'change' ? 'neutral'
                    : h.state === 'reject' ? 'accent-red' : undefined}
              >
                {label}
              </Counter>
            )}
            {h.overdue && (h.state === 'none' || h.state === 'change') && (
              <Counter mode="primary" appearance="accent-red">Просрочено</Counter>
            )}
          </div>
        }
        subtitle={[
          fmtDue(h.due),
          h.late && h.state !== 'none' ? 'сдано с опозданием' : '',
          h.task.length > 80 ? h.task.slice(0, 80) + '…' : h.task,
        ].filter(Boolean).join(' · ') || undefined}
      >
        {h.subject}
      </SimpleCell>

      {expanded && (
        <div style={{ padding: '0 16px 12px' }}>
          <Caption style={{
            color: 'var(--vkui--color_text_secondary)',
            display: 'block', whiteSpace: 'pre-wrap', marginBottom: 8,
          }}>
            {h.task}
          </Caption>

          {h.state === 'change' && h.teacher_note && (
            <Caption style={{
              color: 'var(--vkui--color_text_negative)',
              display: 'block', marginBottom: 8,
            }}>
              Учитель: {h.teacher_note}
            </Caption>
          )}

          {h.answer_required && h.answer && h.state !== 'change' && (
            <Caption style={{
              color: 'var(--vkui--color_text_secondary)',
              display: 'block', marginBottom: 8,
            }}>
              Ваш ответ: {h.answer}
            </Caption>
          )}

          {h.materials.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <Caption style={{
                color: 'var(--vkui--color_text_secondary)',
                display: 'block', marginBottom: 4,
              }}>
                Материалы:
              </Caption>
              {h.materials.map(a => (
                <a
                  key={a.url}
                  href={a.url}
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
          )}

          {canSubmit && (h.state === 'none' || h.state === 'draft' || h.state === 'change' || h.state === 'reject') ? (
            <>
              {h.answer_required && (
                <Input
                  value={answer}
                  onChange={e => setAnswer(e.target.value)}
                  placeholder="Ваш ответ"
                  aria-label="Ответ на задание"
                  style={{ marginBottom: 8 }}
                />
              )}
              {/* Вложения: фото с камеры/галереи или pdf.
                  capture не ставим — выбор «камера/галерея»
                  даёт сам WebView. */}
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
                  {/* Есть что сдать (обязателен ответ или
                      прикреплены файлы) — «Сдать»; нечего
                      сдавать — «Сделано» (как в Classroom). */}
                  {(h.answer_required || files.length > 0) ? 'Сдать' : 'Сделано'}
                </Button>
              </div>
              {files.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  {files.map((f, i) => (
                    <Caption
                      key={`${f.name}-${i}`}
                      style={{
                        color: 'var(--vkui--color_text_secondary)',
                        display: 'block',
                      }}
                    >
                      {f.name} ({Math.round(f.size / 1024)} КБ)
                    </Caption>
                  ))}
                </div>
              )}
            </>
          ) : (
            h.state === 'submit' && (
              <Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>
                Ждёт проверки учителя
              </Caption>
            )
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Карточка-блок со списком ДЗ. Заголовок ВНУТРИ карточки (строка с
 * паддингом), контент ниже. ВАЖНО: контент кладём напрямую в Card, без
 * Group — у .vkuiGroup__host:first-of-type в VKUI жёсткое
 * border-top-*-radius: 0, Group съедает верхнее скругление Card.
 */
export const HomeworkCardList: React.FC<{
  items: HomeworkItem[];
  title?: React.ReactNode;
  /** Ссылка «Все задания →» справа от заголовка (на главной — на вкладку). */
  afterTitle?: React.ReactNode;
  canSubmit?: boolean;
  onSubmit?: (id: number, answer: string, files: { filename: string; mimetype: string; b64: string }[]) => Promise<string | null>;
  onUpdated?: () => void;
}> = ({ items, title = 'Домашние задания', afterTitle, canSubmit, onSubmit, onUpdated }) => (
  <div style={{ margin: '0 8px 8px' }}>
    <VkCard mode="shadow" style={{ overflow: 'hidden' }}>
      {title != null && (
        <div style={{ padding: '12px 16px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {title}
          {afterTitle}
        </div>
      )}
      {items.length === 0 ? (
        <Div><Caption style={{ color: 'var(--vkui--color_text_secondary)' }}>Заданий нет — можно отдыхать</Caption></Div>
      ) : (
        items.map(h => (
          <HomeworkRowItem
            key={h.id}
            h={h}
            canSubmit={canSubmit}
            onSubmit={onSubmit}
            onUpdated={onUpdated}
          />
        ))
      )}
    </VkCard>
  </div>
);
