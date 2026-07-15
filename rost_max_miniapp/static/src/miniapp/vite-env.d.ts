/// <reference types="vite/client" />

// SVG, импортируемый с суффиксом ?react, отдаётся как
// React-компонент (встроенная фича Vite). Декларация нужна,
// т.к. vite/client объявляет только `*.svg` (URL-строка).
// Тип элемента не уточняем (any) — достаточно для props-прокидки
// style={width,height}.
declare module '*.svg?react' {
  import type { FC } from 'react';
  const ReactComponent: FC<any>;
  export default ReactComponent;
}
