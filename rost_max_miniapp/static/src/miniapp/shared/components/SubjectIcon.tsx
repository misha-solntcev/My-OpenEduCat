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

export const subjectTint = (color: number): React.CSSProperties => color
  ? { background: TINTS[((color - 1) % 55) + 1], color: 'var(--vkui--color_text_primary)' }
  : { background: 'var(--vkui--color_background_secondary)', color: 'var(--vkui--color_text_secondary)' };
