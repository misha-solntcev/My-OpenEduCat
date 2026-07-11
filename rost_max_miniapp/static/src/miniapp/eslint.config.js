import js from '@eslint/js';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';
import boundaries from 'eslint-plugin-boundaries';

export default [
  {
    ignores: ['bundle/**', 'node_modules/**', 'dist/**', '*.config.ts', '*.config.js'],
  },
  js.configs.recommended,
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 2021,
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
      globals: {
        window: 'readonly',
        document: 'readonly',
        React: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        sessionStorage: 'readonly',
        alert: 'readonly',
        setTimeout: 'readonly',
        HTMLInputElement: 'readonly',
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
      boundaries: boundaries,
    },
    settings: {
      boundaries: {
        elements: [
          { type: 'app', pattern: 'app' },
          { type: 'pages', pattern: 'pages' },
          { type: 'widgets', pattern: 'widgets' },
          { type: 'features', pattern: 'features' },
          { type: 'entities', pattern: 'entities' },
          { type: 'shared', pattern: 'shared' },
          { type: 'node_modules', pattern: 'node_modules' },
        ],
      },
    },
    rules: {
      // Отключаем базовое (не знает про TS-типы), используем TS-вариант
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      // FSD-lite: импорты строго ВНИЗ. Запрещены upward-импорты.
      'boundaries/element-types': [
        'error',
        {
          default: 'disallow',
          rules: [
            { from: 'app', allow: ['app', 'pages', 'widgets', 'features', 'entities', 'shared', 'node_modules'] },
            { from: 'pages', allow: ['pages', 'widgets', 'features', 'entities', 'shared', 'node_modules'] },
            { from: 'widgets', allow: ['widgets', 'features', 'entities', 'shared', 'node_modules'] },
            { from: 'features', allow: ['features', 'entities', 'shared', 'node_modules'] },
            { from: 'entities', allow: ['entities', 'shared', 'node_modules'] },
            { from: 'shared', allow: ['shared', 'node_modules'] },
          ],
        },
      ],
      'boundaries/no-unknown': 'error',
    },
  },
];
