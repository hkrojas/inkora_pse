/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // === Stitch PrintFlow Design System ===
        // Primary: Navy Editorial  
        primary: {
          DEFAULT: '#001d44',
          container: '#00326b',
          fixed: '#d7e2ff',
          'fixed-dim': '#abc7ff'
        },
        // Secondary: Emerald
        secondary: {
          DEFAULT: '#006c48',
          container: '#8bf8c2',
          fixed: '#8bf8c2',
          'fixed-dim': '#6edba7'
        },
        // Tertiary: Gold
        tertiary: {
          DEFAULT: '#735c00',
          container: '#cca830',
          fixed: '#ffe088',
          'fixed-dim': '#e9c349'
        },
        // Surface hierarchy
        surface: {
          DEFAULT: '#f9f9fd',
          bright: '#f9f9fd',
          dim: '#d9dadd',
          container: {
            DEFAULT: '#edeef1',
            low: '#f3f3f7',
            lowest: '#ffffff',
            high: '#e7e8eb',
            highest: '#e2e2e6'
          },
          variant: '#e2e2e6',
          tint: '#255dad'
        },
        background: '#f9f9fd',
        // On-surface semantic
        on: {
          background: '#191c1e',
          surface: {
            DEFAULT: '#191c1e',
            variant: '#43474f'
          },
          primary: '#ffffff',
          'primary-container': '#6b9bef',
          'primary-fixed': '#001b3f',
          'primary-fixed-variant': '#00458f',
          secondary: '#ffffff',
          'secondary-container': '#00734d',
          'secondary-fixed': '#002113',
          'secondary-fixed-variant': '#005235',
          tertiary: '#ffffff',
          'tertiary-container': '#4f3e00',
          'tertiary-fixed': '#241a00',
          'tertiary-fixed-variant': '#574500',
          error: '#ffffff',
          'error-container': '#93000a'
        },
        // Outline
        outline: {
          DEFAULT: '#737780',
          variant: '#c3c6d1'
        },
        // Error
        error: {
          DEFAULT: '#ba1a1a',
          container: '#ffdad6'
        },
        // Inverse
        inverse: {
          surface: '#2e3133',
          'on-surface': '#f0f0f4',
          primary: '#abc7ff'
        },
        // Semantic (preserved from previous)
        success: {
          DEFAULT: '#006c48',
          container: '#8bf8c2'
        },
        warning: {
          DEFAULT: '#735c00',
          container: '#ffe088'
        },
        info: {
          DEFAULT: '#255dad',
          container: '#d7e2ff'
        },
        scrim: '#191c1e'
      },
      fontFamily: {
        headline: ['Manrope', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        label: ['Inter', 'sans-serif'],
        sans: ['Inter', 'sans-serif']
      },
      borderRadius: {
        DEFAULT: '0.125rem',
        sm: '0.25rem',
        md: '0.5rem',
        lg: '0.75rem',
        xl: '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem'
      },
      keyframes: {
        'page-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        'slide-active': {
          '0%': { transform: 'scaleY(0)' },
          '100%': { transform: 'scaleY(1)' }
        }
      },
      animation: {
        'page-in': 'page-in 0.5s ease-out forwards',
        'fade-up': 'fade-up 0.6s ease-out forwards',
        'slide-active': 'slide-active 0.3s ease-out forwards'
      }
    }
  },
  plugins: []
};
