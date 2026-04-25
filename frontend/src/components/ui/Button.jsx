import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils/cn';

const variants = {
  primary: 'bg-[var(--color-primary)] text-[var(--color-primary-text)] hover:bg-[var(--color-primary-hover)] shadow-[var(--shadow-primary)]',
  secondary: 'bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] hover:bg-[var(--color-surface-soft)]',
  soft: 'bg-[var(--color-primary-soft)] text-[var(--color-primary)] hover:opacity-90',
  ghost: 'bg-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)]',
  danger: 'bg-[var(--color-danger)] text-white hover:opacity-90',
};

const sizes = {
  sm: 'h-8 px-3 text-xs rounded-xl',
  md: 'h-10 px-4 text-sm rounded-[13px]',
  lg: 'h-12 px-5 text-[15px] rounded-2xl',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  className,
  disabled,
  ...props
}) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-extrabold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-px active:translate-y-0',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
