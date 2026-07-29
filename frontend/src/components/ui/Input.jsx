import { cn } from '../../lib/utils/cn';

export default function Input({
  label,
  helper,
  error,
  className,
  id,
  ...props
}) {
  const inputId = id || (label ? `input-${Math.random().toString(36).slice(2, 9)}` : undefined);

  return (
    <div className={cn('grid gap-2', className)}>
      {label && (
        <label htmlFor={inputId} className="text-[13px] font-extrabold text-[var(--color-text)]">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={cn(
          'w-full min-h-[44px] rounded-[14px] border bg-[var(--color-surface)] px-4 text-sm text-[var(--color-text)] outline-none transition-all',
          'placeholder:text-[var(--color-text-soft)]',
          error
            ? 'border-[var(--color-danger)] focus:shadow-[0_0_0_4px_rgba(220,38,38,0.09)]'
            : 'border-[var(--color-border)] focus:border-[var(--color-primary)] focus:shadow-[0_0_0_4px_rgba(163,230,53,0.16)]'
        )}
        {...props}
      />
      {error ? (
        <p className="text-[13px] font-bold text-[var(--color-danger)]">{error}</p>
      ) : helper ? (
        <p className="text-[13px] text-[var(--color-text-muted)] leading-relaxed">{helper}</p>
      ) : null}
    </div>
  );
}
