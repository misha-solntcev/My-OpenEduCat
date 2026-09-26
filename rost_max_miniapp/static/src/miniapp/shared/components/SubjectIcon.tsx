import React from 'react';
import {
  faBolt, faBook, faCalculator, faChartLine, faComments, faDna,
  faDumbbell, faEarthAsia, faFeatherPointed, faFlask, faGraduationCap,
  faLandmark, faLanguage, faLaptopCode, faMasksTheater, faMusic,
  faPalette, faScaleBalanced, faScrewdriverWrench, faShapes,
  faSquareRootVariable,
} from '@fortawesome/free-solid-svg-icons';

/** Иконки предметов из утверждённой палитры design/subject-palette.html. */
const subjectIcon = (subject: string) => {
  const s = subject.toLowerCase();
  if (/вероятн|статистик/.test(s)) return faChartLine;
  if (/геометр/.test(s)) return faShapes;
  if (/алгебр|тригономет/.test(s)) return faSquareRootVariable;
  if (/матем|арифмет|индивидуальн.*проект/.test(s)) return faCalculator;
  if (/физкульт|физическ.*культур|физ-ра|спорт|физра|гимнаст/.test(s)) return faDumbbell;
  if (/физик/.test(s)) return faBolt;
  if (/хими/.test(s)) return faFlask;
  if (/биолог/.test(s)) return faDna;
  if (/англ|ин\.яз|иностран|english/.test(s)) return faLanguage;
  if (/русск/.test(s)) return faFeatherPointed;
  if (/литерат|родн|чтени|^орк/.test(s)) return faBook;
  if (/информат|программир|computer/.test(s)) return faLaptopCode;
  if (/общест|правовед/.test(s)) return faScaleBalanced;
  if (/истори/.test(s)) return faLandmark;
  if (/классн.*час/.test(s)) return faComments;
  if (/географ|природовед|окружающ.*мир/.test(s)) return faEarthAsia;
  if (/музык|пени/.test(s)) return faMusic;
  if (/изо|рисован|черчени/.test(s)) return faPalette;
  if (/мхк|искусств|миров.*художествен.*культур/.test(s)) return faMasksTheater;
  if (/технолог|труд/.test(s)) return faScrewdriverWrench;
  return faGraduationCap;
};

/** Декоративный SVG: название предмета выводится рядом в карточке. */
export const SubjectIcon: React.FC<{ subject: string }> = ({ subject }) => {
  const { icon: [width, height, , , path] } = subjectIcon(subject);
  return (
    <svg width={20} height={20} viewBox={`0 0 ${width} ${height}`}
      fill="currentColor" aria-hidden="true" focusable="false">
      {Array.isArray(path)
        ? path.map((d, index) => <path key={index} d={d} />)
        : <path d={path} />}
    </svg>
  );
};

/* Пастельный фон квадрата предмета — та же календарная палитра Odoo
   (index = ((c-1)%55)+1), что в TeacherHomeworkCards.subjectColor.
   Экспортируется для шапки экрана задания (мокап D: иконка предмета
   перед названием). */
const TINTS = ['#cccccc', '#f68c8c', '#ecbc8f', '#f2da83', '#a3c4ec', '#caa9c1', '#ebbeaa', '#96d0cc',
  '#8d9cee', '#f68dbf', '#a8deaf', '#c6b1f1', '#d09cae', '#8ddeba', '#c6b393', '#fbe484',
  '#97bcf9', '#c187d0', '#e87ea7', '#7f9598', '#8fc19f', '#d09392', '#b5a29a', '#a6748e',
  '#aef1bc', '#c7c7ab', '#f3e7a9', '#d6acac', '#dbdee0', '#aac2b2', '#f373ff', '#ff7388',
  '#bfe373', '#73dcd3', '#73adff', '#d373dc', '#dc7383', '#dca973', '#c0ff73', '#73f8ff',
  '#739bd5', '#ff73e5', '#ffce73', '#93e373', '#73d7dc', '#739aff', '#dcb773', '#75ff73',
  '#73e5ff', '#7390dc', '#ff73c0', '#73dc9b', '#73c3d5', '#7375ff', '#d573a9', '#aac2b2'];

const SUBJECT_BASE_COLORS = [
  '#a2a2a2', '#ee2d2d', '#dc8534', '#e8bb1d', '#5794dd', '#9f628f', '#db8865', '#41a9a2',
  '#304be0', '#ee2f8a', '#61c36e', '#9872e6', '#aa4b6b', '#30c381', '#97743a', '#f7cd1f',
  '#4285f4', '#8e24aa', '#d6145f', '#173e43', '#348f50', '#aa3a38', '#795548', '#5e0231',
  '#6be585', '#999966', '#e9d362', '#b56969', '#bdc3c7', '#649173', '#ea00ff', '#ff0026',
  '#8bcc00', '#00bfaf', '#006aff', '#af00bf', '#bf001d', '#bf6300', '#8cff00', '#00f2ff',
  '#004ab3', '#ff00d0', '#ffa600', '#3acc00', '#00b6bf', '#0048ff', '#bf7c00', '#04ff00',
  '#00d0ff', '#0036bf', '#ff008c', '#00bf49', '#0092b3', '#0004ff', '#b20062', '#649173',
];

/** Затемняет цвет предмета до контраста не ниже 3:1 к пастельному фону. */
const contrastingIconColor = (base: string, bg: string): string => {
  const rgb = (hex: string) => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  const luminance = (channels: number[]) => {
    const [r, g, b] = channels.map(channel => {
      const value = channel / 255;
      return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
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

const SUBJECT_COLORS = TINTS.map((bg, index) => ({
  bg,
  color: contrastingIconColor(SUBJECT_BASE_COLORS[index], bg),
}));

/** Единые цвета квадрата предмета: тот же расчёт, что в карточках ДЗ. */
export const subjectColor = (color: number): { bg: string; color: string } => {
  if (!color) {
    return {
      bg: 'var(--vkui--color_background_secondary)',
      color: 'var(--vkui--color_text_secondary)',
    };
  }
  return SUBJECT_COLORS[((color - 1) % 55) + 1];
};

/** Квадрат-аватар предмета: пастель из БД + глиф по названию.
 *  ЕДИНСТВЕННЫЙ источник правды для всех экранов (лента ДЗ, вкладка
 *  «Задания», «Оценки», экран задания) — раньше палитра дублировалась
 *  в трёх файлах и иконки в «Оценках» рендерились чёрными. */
export const SubjectAvatar: React.FC<{ subject: string; color?: number; size?: number }> = ({
  subject, color = 0, size = 38,
}) => {
  const c = subjectColor(color);
  return (
    <span style={{
      width: size, height: size, borderRadius: 10, flexShrink: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: c.bg, color: c.color,
    }}>
      <SubjectIcon subject={subject} />
    </span>
  );
};
