import Button from './Button';

export default function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  action, // legacy compat
}) {
  return (
    <div className="empty-state-anim rounded-3xl border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-soft)] px-6 py-10 text-center">
      <div className="empty-state-anim__icon mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
        {icon}
      </div>

      <h3 className="empty-state-anim__title mb-2 text-lg font-extrabold tracking-tight text-[var(--color-text)]">
        {title}
      </h3>

      <p className="empty-state-anim__desc mx-auto mb-5 max-w-md text-sm leading-6 text-[var(--color-text-muted)]">
        {description}
      </p>

      {actionLabel && (
        <div className="empty-state-anim__action">
          <Button onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}

      {action && (
        <div className="empty-state-anim__action">
          {action}
        </div>
      )}
    </div>
  );
}
