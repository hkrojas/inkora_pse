import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils/cn';

const variants = {
  primary: 'bg-[var(--color-primary)] text-[var(--color-primary-text)] hover:bg-[var(--color-primary-hover)] shadow-[var(--shadow-primary)] active:scale-[0.97]',
  secondary: 'bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] hover:bg-[var(--color-surface-soft)] active:scale-[0.97]',
  soft: 'bg-[var(--color-primary-soft)] text-[var(--color-primary)] hover:opacity-90 active:scale-[0.97]',
  ghost: 'bg-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)] active:scale-[0.97]',
  danger: 'bg-[var(--color-danger)] text-white hover:opacity-90 active:scale-[0.97]',
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
        'inline-flex items-center justify-center gap-2 font-extrabold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-px disabled:hover:translate-y-0 disabled:active:scale-100',
        loading && 'btn-loading',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {loading && (
        <span className="btn-loading__spinner">
          <Loader2 className="h-4 w-4 animate-spin" />
        </span>
      )}
      <span className={cn('inline-flex items-center gap-2', loading && 'btn-loading__label')}>
        {children}
      </span>
    </button>
  );
}
