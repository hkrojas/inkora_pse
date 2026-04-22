/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // === Inkora Design System — colores extraídos del logo ===
        // Gradiente del logo: #2563EB → #7C3AED → #9333EA

        // Primary: Inkora Blue
        primary: {
          DEFAULT: '#2563EB',
          hover: '#1d4ed8',
          dark: '#1e2d6e',
          fixed: '#EFF6FF',
          'fixed-dim': '#BFDBFE',
        },
        // Secondary: Inkora Violet
        secondary: {
          DEFAULT: '#7C3AED',
          hover: '#6d28d9',
          fixed: '#F5F3FF',
          'fixed-dim': '#DDD6FE',
        },
        // Accent: Inkora Purple (fin del gradiente)
        accent: {
          DEFAULT: '#9333EA',
          hover: '#7e22ce',
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
            highest: '#e2e2e6',
          },
          variant: '#e2e2e6',
        },
        background: '#f9f9fd',
        // On-surface
        on: {
          background: '#191c1e',
          surface: {
            DEFAULT: '#191c1e',
            variant: '#43474f',
          },
          primary: '#ffffff',
          secondary: '#ffffff',
          error: '#ffffff',
        },
        // Outline
        outline: {
          DEFAULT: '#737780',
          variant: '#c3c6d1',
        },
        // Semantic
        success: {
          DEFAULT: '#059669',
          container: '#D1FAE5',
        },
        warning: {
          DEFAULT: '#D97706',
          container: '#FEF3C7',
        },
        error: {
          DEFAULT: '#DC2626',
          container: '#FEE2E2',
        },
        info: {
          DEFAULT: '#0891B2',
          container: '#CFFAFE',
        },
        scrim: '#191c1e',
      },
      fontFamily: {
        brand: ['Syne', 'sans-serif'],
        heading: ['Space Grotesk', 'Inter', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        label: ['Space Mono', 'monospace'],
        sans: ['Inter', 'sans-serif'],
        mono: ['Space Mono', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '0.125rem',
        xs: '2px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '24px',
        '3xl': '32px',
      },
      backgroundImage: {
        'inkora-gradient': 'linear-gradient(135deg, #2563EB, #7C3AED)',
        'inkora-gradient-full': 'linear-gradient(135deg, #2563EB 0%, #7C3AED 60%, #9333EA 100%)',
        'inkora-gradient-dark': 'linear-gradient(135deg, #6366F1, #818CF8)',
      },
      keyframes: {
        'page-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-active': {
          '0%': { transform: 'scaleY(0)' },
          '100%': { transform: 'scaleY(1)' },
        },
        'logo-drift': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-4px)' },
        },
      },
      animation: {
        'page-in': 'page-in 0.5s ease-out forwards',
        'fade-up': 'fade-up 0.6s ease-out forwards',
        'slide-active': 'slide-active 0.3s ease-out forwards',
        'logo-drift': 'logo-drift 4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
