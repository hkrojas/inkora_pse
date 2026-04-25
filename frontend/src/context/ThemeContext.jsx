import { createContext, useContext, useState, useEffect, useCallback } from 'react';

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

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    const stored = getStoredTheme();
    return stored || 'system';
  });

  const [noise, setNoiseState] = useState(() => {
    const stored = getStoredNoise();
    return stored === '1';
  });

  const resolvedTheme = theme === 'system' ? getSystemTheme() : theme;

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(resolvedTheme);

    // Keep data-theme for backward compatibility with old CSS
    root.dataset.theme = resolvedTheme;

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute(
        'content',
        resolvedTheme === 'dark' ? '#0B0B14' : '#F4F3FF'
      );
    }
  }, [resolvedTheme]);

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

  const setTheme = useCallback((next) => {
    setThemeState(next);
    storeTheme(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((current) => {
      const resolved = current === 'system' ? getSystemTheme() : current;
      const next = resolved === 'dark' ? 'light' : 'dark';
      storeTheme(next);
      return next;
    });
  }, []);

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
