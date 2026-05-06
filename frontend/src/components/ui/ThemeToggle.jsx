import { Moon, Sun } from 'lucide-react';
import { cn } from '../../lib/utils/cn';

export default function ThemeToggle({ theme, setTheme, className }) {
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={(event) => setTheme(isDark ? 'light' : 'dark', event)}
      className={cn(
        'inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors',
        className
      )}
      aria-label={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
