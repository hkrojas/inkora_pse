export default function FormField({
  label,
  icon: Icon,
  children,
  error,
  hint,
  required = false,
  className = '',
}) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`.trim()}>
      <label className="flex items-center gap-1.5 text-xs font-bold text-[var(--color-text)]">
        {Icon && (
          <span className="inline-flex h-4 w-4 items-center justify-center text-[var(--color-primary)]">
            <Icon className="h-3.5 w-3.5" />
          </span>
        )}
        <span>{label}</span>
        {required && <span className="text-[var(--color-danger)]">*</span>}
      </label>
      {children}
      {hint && !error && (
        <p className="text-[11px] text-[var(--color-text-muted)]">{hint}</p>
      )}
      {error && (
        <p className="text-[11px] font-semibold text-[var(--color-danger)]">{error}</p>
      )}
    </div>
  );
}
