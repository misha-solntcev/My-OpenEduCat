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
