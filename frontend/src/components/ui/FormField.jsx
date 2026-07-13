import { cloneElement, isValidElement, useId } from 'react';

export default function FormField({
  label,
  icon: Icon,
  children,
  error,
  hint,
  required = false,
  className = '',
}) {
  const labelId = useId();
  const hintId = useId();
  const errorId = useId();
  const descriptionId = error ? errorId : (hint ? hintId : undefined);
  const isNativeControl = isValidElement(children)
    && typeof children.type === 'string'
    && ['input', 'select', 'textarea'].includes(children.type);
  const enhancedChildren = isNativeControl
    ? cloneElement(children, {
        'aria-labelledby': children.props['aria-labelledby'] || labelId,
        'aria-describedby': [children.props['aria-describedby'], descriptionId].filter(Boolean).join(' ') || undefined,
        'aria-invalid': children.props['aria-invalid'] ?? Boolean(error),
      })
    : children;

  return (
    <div
      className={`flex flex-col gap-1.5 ${className}`.trim()}
      role="group"
      aria-labelledby={labelId}
      aria-describedby={descriptionId}
    >
      <span id={labelId} className="flex items-center gap-1.5 text-xs font-bold text-[var(--color-text)]">
        {Icon && (
          <span className="inline-flex h-4 w-4 items-center justify-center text-[var(--color-primary)]">
            <Icon className="h-3.5 w-3.5" />
          </span>
        )}
        <span>{label}</span>
        {required && <span className="text-[var(--color-danger)]">*</span>}
      </span>
      {enhancedChildren}
      {hint && !error && (
        <p id={hintId} className="text-[11px] text-[var(--color-text-muted)]">{hint}</p>
      )}
      {error && (
        <p id={errorId} className="text-[11px] font-semibold text-[var(--color-danger)]">{error}</p>
      )}
    </div>
  );
}
