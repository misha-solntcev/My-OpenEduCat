// Общий тип активного таба: нужен и App.tsx, и navRestore.ts (импорт типа
// из App.tsx создал бы цикл App -> navRestore -> App).

export type TabId = 'dashboard' | 'timetable' | 'subjects';
