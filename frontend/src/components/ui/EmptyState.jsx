import Button from './Button';

export default function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}) {
  return (
    <div className="rounded-3xl border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-soft)] px-6 py-10 text-center">
      <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
        {icon}
      </div>

      <h3 className="mb-2 text-lg font-extrabold tracking-tight text-[var(--color-text)]">
        {title}
      </h3>

      <p className="mx-auto mb-5 max-w-md text-sm leading-6 text-[var(--color-text-muted)]">
        {description}
      </p>

      {actionLabel && (
        <Button onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
