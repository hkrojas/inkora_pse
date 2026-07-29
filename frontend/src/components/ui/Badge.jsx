import { cn } from '../../lib/utils/cn';

const variants = {
  draft: 'bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]',
  sent: 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]',
  accepted: 'bg-[var(--color-purple-soft)] text-[var(--color-purple-text)]',
  paid: 'bg-[var(--color-success-soft)] text-[var(--color-success-text)]',
  partial: 'bg-[var(--color-warning-soft)] text-[var(--color-warning-text)]',
  overdue: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]',
  cancelled: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]',
  /* Legacy variants for compatibility */
  default: 'bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]',
  success: 'bg-[var(--color-success-soft)] text-[var(--color-success-text)]',
  warning: 'bg-[var(--color-warning-soft)] text-[var(--color-warning-text)]',
  danger: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]',
  error: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]',
  info: 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]',
  brand: 'bg-[var(--color-purple-soft)] text-[var(--color-purple-text)]',
  outline: 'border border-[var(--color-border)] text-[var(--color-text-muted)]',
  pending: 'bg-[var(--color-warning-soft)] text-[var(--color-warning-text)]',
  rejected: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]',
  observed: 'bg-[var(--color-warning-soft)] text-[var(--color-warning-text)]',
  activo: 'bg-[var(--color-success-soft)] text-[var(--color-success-text)]',
  inactivo: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]',
  trial: 'bg-[var(--color-purple-soft)] text-[var(--color-purple-text)]',
  facturado: 'bg-[var(--color-success-soft)] text-[var(--color-success-text)]',
};

export default function Badge({ children, variant = 'draft', className }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full px-2.5 py-1.5 text-xs font-black',
        'before:h-1.5 before:w-1.5 before:rounded-full before:bg-current',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function statusBadge(estado) {
  const map = {
    pendiente: 'pending',
    pendiente_smartpse: 'warning',
    pagado: 'paid',
    parcial: 'partial',
    vencido: 'overdue',
    anulada: 'cancelled',
    emitida: 'success',
    borrador: 'draft',
    aceptada: 'accepted',
    rechazada: 'rejected',
    observada: 'observed',
    facturado: 'facturado',
    activo: 'activo',
    inactivo: 'inactivo',
    trial: 'trial',
  };
  return map[estado] || 'default';
}
