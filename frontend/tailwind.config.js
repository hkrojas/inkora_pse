/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        inkora: {
          bg: 'var(--color-bg)',
          surface: 'var(--color-surface)',
          soft: 'var(--color-surface-soft)',
          text: 'var(--color-text)',
          muted: 'var(--color-text-muted)',
          border: 'var(--color-border)',
          primary: 'var(--color-primary)',
          success: 'var(--color-success)',
          warning: 'var(--color-warning)',
          danger: 'var(--color-danger)',
        }
      },
      borderRadius: {
        inkora: 'var(--radius-lg)'
      },
      boxShadow: {
        inkora: 'var(--shadow-card)'
      }
    }
  },
  plugins: [],
};
