/**
 * Поле ввода: скрепка слева (слот before), опциональная кнопка отправки
 * справа (слот after) — общий компонент для трёх мест: ДЗ в карточке урока,
 * ответ ученика, «Текст задания» при правке и чат сдачи.
 *
 * Раньше в этих местах повторялась одна и та же ручная конструкция:
 * контейнер с `position: relative`, кнопка `absolute` поверх поля и
 * `paddingRight` у самого элемента управления, иначе текст ложился под
 * скрепку. Обвязка не нужна вовсе: у `Textarea` в VKUI 8 есть штатный слот
 * `after` под иконку справа (и рекомендация использовать IconButton), и
 * VKUI сам резервирует место и сдвигает текст. Именно поэтому компонент
 * сделан на Textarea, а не на Input: у Input слот под отступ называется
 * `input`, у Textarea — `textArea`, и ручное задание отступа в каждом месте
 * было источником ошибок. Теперь отступ не задаётся нигде.
 *
 * Textarea, а не Input: домашнее задание бывает длинным («§14, №412–418»,
 * а иногда развёрнутое задание на пол-экрана), и однострочное поле его
 * обрезает. Заодно у Textarea включён `grow` — поле само растёт под контент
 * до maxHeight, то есть короткий текст не занимает место зря.
 *
 * Форма строки — мессенджерская (2026-10, Миша): скрепка СЛЕВА (слот
 * before), опциональная кнопка отправки СПРАВА (слот after) — как в
 * современных чатах. VKUI FormField даёт оба слота, CSS не нужен.
 * Кнопка отправки рендерится только там, где передан onSend (сейчас —
 * чат сдачи HwChat); остальные места (ДЗ, ответ, задание) остались
 * «текст + скрепка».
 *
 * attachProps приходит из хука загрузки файлов (useLessonMaterials в карточке
 * урока и useAttachFiles на странице задания) — у них разные эндпоинты и
 * права, поэтому сам хук остаётся у вызова.
 */
import React from 'react';
import { Textarea, IconButton } from '@vkontakte/vkui';
import { Icon28AttachOutline, Icon24Send } from '@vkontakte/icons';

/** Потолок роста поля в px. Textarea с grow растёт под текст сам, но без
 *  ограничения длинное задание занимало бы весь экран и выталкивало бы
 *  кнопки «Выдать»/«Ок» за пределы экрана. */
export const HW_MAX_HEIGHT = 120;

export type AttachProps = {
  /* Тип onClick берём из ButtonHTMLAttributes: IconButton требует
     MouseEventHandler, и наш жесткий (e: React.MouseEvent) с ним не
     совместим. */
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  /** Загрузка файла: скрепка неактивна, пока идёт отправка. */
  disabled?: boolean;
};

export interface AttachFieldProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  /** aria-label поля — обязателен: иначе скринридер читает безымянный ввод. */
  ariaLabel: string;
  /** Пропы кнопки скрепки из хука загрузки. */
  attachProps: AttachProps;
  /** Скрытый input[type=file] из того же хука. */
  hiddenInput?: React.ReactNode;
  disabled?: boolean;
  /** Потолок роста поля. grow подстраивает высоту под текст, но не даёт
   *  полю съесть весь экран на длинном задании. */
  maxHeight?: number;
  /** Кнопка отправки справа (чат сдачи). Не передана — строки без неё. */
  onSend?: () => void;
  /** Неактивная отправка: пустой текст/файлы, идёт отправка. */
  sendDisabled?: boolean;
}

export const AttachField: React.FC<AttachFieldProps> = ({
  value, onChange, placeholder, ariaLabel, attachProps, hiddenInput,
  disabled, maxHeight, onSend, sendDisabled,
}) => (
  <>
    <Textarea
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={ariaLabel}
      disabled={disabled}
      maxHeight={maxHeight}
      before={(
        /* У IconButton в VKUI 8 нет ни пропа icon, ни mode/size: иконка
           передаётся как children, а текст для скринридера — через label
           (не aria-label). Поэтому именно такая форма. */
        <IconButton
          onClick={attachProps.onClick}
          disabled={Boolean(disabled) || Boolean(attachProps.disabled)}
          label="Прикрепить фото или файл"
        >
          <Icon28AttachOutline width={20} height={20} />
        </IconButton>
      )}
      after={onSend ? (
        <IconButton
          onClick={onSend}
          disabled={Boolean(disabled) || Boolean(sendDisabled)}
          label="Отправить сообщение"
        >
          <Icon24Send />
        </IconButton>
      ) : undefined}
    />
    {hiddenInput}
  </>
);