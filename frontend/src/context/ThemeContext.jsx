import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const ThemeContext = createContext(null);
const THEME_KEY = 'inkora-theme';
const NOISE_KEY = 'inkora-noise';

function getSystemTheme() {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function getStoredTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

function storeTheme(theme) {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // ignore
  }
}

function getStoredNoise() {
  try {
    return localStorage.getItem(NOISE_KEY);
  } catch {
    return null;
  }
}

function storeNoise(value) {
  try {
    localStorage.setItem(NOISE_KEY, value ? '1' : '0');
  } catch {
    // ignore
  }
}

function getOriginPoint(origin) {
  if (typeof window === 'undefined') return { x: '100%', y: '0%' };

  const fallback = { x: `${window.innerWidth - 32}px`, y: '32px' };
  if (!origin) return fallback;

  const target = origin.currentTarget || origin.target;
  if (target?.getBoundingClientRect) {
    const rect = target.getBoundingClientRect();
    return {
      x: `${rect.left + rect.width / 2}px`,
      y: `${rect.top + rect.height / 2}px`,
    };
  }

  if (Number.isFinite(origin.clientX) && Number.isFinite(origin.clientY)) {
    return { x: `${origin.clientX}px`, y: `${origin.clientY}px` };
  }

  if (Number.isFinite(origin.x) && Number.isFinite(origin.y)) {
    return { x: `${origin.x}px`, y: `${origin.y}px` };
  }

  return fallback;
}

export function ThemeProvider({ children }) {
  const mountedRef = useRef(false);
  const transitionTimeoutRef = useRef(null);
  const [theme, setThemeState] = useState(() => {
    const stored = getStoredTheme();
    return stored || 'system';
  });

  const [noise, setNoiseState] = useState(() => {
    const stored = getStoredNoise();
    return stored === '1';
  });

  const resolvedTheme = theme === 'system' ? getSystemTheme() : theme;

  const startThemeTransition = useCallback((nextResolvedTheme, origin) => {
    if (!mountedRef.current || nextResolvedTheme === resolvedTheme || typeof document === 'undefined') {
      return;
    }

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    const root = document.documentElement;
    const isOperationalSurface = Boolean(document.querySelector('.app-dashboard-shell'));

    if (transitionTimeoutRef.current) {
      window.clearTimeout(transitionTimeoutRef.current);
    }

    root.classList.remove(
      'theme-switching',
      'theme-switching--light',
      'theme-switching--dark',
      'theme-switching--from-light',
      'theme-switching--from-dark',
      'theme-switching--operational',
    );

    if (isOperationalSurface) {
      root.style.setProperty(
        '--theme-transition-color',
        resolvedTheme === 'dark' ? '#101610' : '#f3f6f1',
      );
      root.classList.add('theme-switching', 'theme-switching--operational');
    } else {
      const { x, y } = getOriginPoint(origin);
      root.style.setProperty('--theme-origin-x', x);
      root.style.setProperty('--theme-origin-y', y);
      root.classList.add('theme-switching', `theme-switching--${nextResolvedTheme}`);
    }

    void root.offsetWidth;

    transitionTimeoutRef.current = window.setTimeout(() => {
      root.classList.remove(
        'theme-switching',
        'theme-switching--light',
        'theme-switching--dark',
        'theme-switching--from-light',
        'theme-switching--from-dark',
        'theme-switching--operational',
      );
      root.style.removeProperty('--theme-origin-x');
      root.style.removeProperty('--theme-origin-y');
      root.style.removeProperty('--theme-transition-color');
      transitionTimeoutRef.current = null;
    }, isOperationalSurface ? 240 : 760);
  }, [resolvedTheme]);

  useEffect(() => {
    const root = document.documentElement;

    root.classList.remove('light', 'dark');
    root.classList.add(resolvedTheme);

    // Keep data-theme for backward compatibility with old CSS
    root.dataset.theme = resolvedTheme;

    if (!mountedRef.current) {
      mountedRef.current = true;
    }

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute(
        'content',
        resolvedTheme === 'dark' ? '#101610' : '#f3f6f1'
      );
    }

  }, [resolvedTheme]);

  useEffect(() => {
    return () => {
      if (transitionTimeoutRef.current) {
        window.clearTimeout(transitionTimeoutRef.current);
        transitionTimeoutRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (noise) {
      root.classList.add('u-noise');
    } else {
      root.classList.remove('u-noise');
    }
  }, [noise]);

  useEffect(() => {
    if (theme !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => setThemeState('system');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);

  const setTheme = useCallback((next, origin) => {
    const nextResolvedTheme = next === 'system' ? getSystemTheme() : next;
    startThemeTransition(nextResolvedTheme, origin);
    setThemeState(next);
    storeTheme(next);
  }, [startThemeTransition]);

  const toggleTheme = useCallback((origin) => {
    const currentResolved = theme === 'system' ? getSystemTheme() : theme;
    const next = currentResolved === 'dark' ? 'light' : 'dark';
    startThemeTransition(next, origin);
    storeTheme(next);
    setThemeState(next);
  }, [startThemeTransition, theme]);

  const setNoise = useCallback((value) => {
    setNoiseState(value);
    storeNoise(value);
  }, []);

  const toggleNoise = useCallback(() => {
    setNoiseState((current) => {
      const next = !current;
      storeNoise(next);
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, toggleTheme, noise, setNoise, toggleNoise }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
