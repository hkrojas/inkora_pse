import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';

const browserGlobals = {
  window: 'readonly',
  document: 'readonly',
  console: 'readonly',
  localStorage: 'readonly',
  sessionStorage: 'readonly',
  setTimeout: 'readonly',
  clearTimeout: 'readonly',
  URL: 'readonly',
  Blob: 'readonly',
  FormData: 'readonly',
  fetch: 'readonly',
  navigator: 'readonly',
  history: 'readonly',
  FileReader: 'readonly',
};

export default [
  {
    files: ['src/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: browserGlobals,
    },
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'off',
      'no-unused-vars': 'off',
      'no-restricted-globals': [
        'error',
        { name: 'alert', message: 'Usa los diálogos propios de Inkora.' },
        { name: 'confirm', message: 'Usa useInkoraDialog().confirmAction().' },
        { name: 'prompt', message: 'Usa los diálogos propios de Inkora.' },
      ],
      'no-restricted-properties': [
        'error',
        { object: 'window', property: 'alert', message: 'Usa los diálogos propios de Inkora.' },
        { object: 'window', property: 'confirm', message: 'Usa useInkoraDialog().confirmAction().' },
        { object: 'window', property: 'prompt', message: 'Usa los diálogos propios de Inkora.' },
      ],
    },
  },
];
