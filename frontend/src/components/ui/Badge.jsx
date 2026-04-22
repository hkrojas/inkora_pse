const variants = {
  default: 'badge badge--neutral',
  success: 'badge badge--success',
  warning: 'badge badge--warning',
  danger: 'badge badge--error',
  info: 'badge badge--info',
  brand: 'badge badge--brand',
  outline: 'badge badge--outline',
  pending: 'badge badge--warning',
  accepted: 'badge badge--success',
  rejected: 'badge badge--error',
  observed: 'badge badge--warning',
};

export default function Badge({ children, variant = 'default', className = '' }) {
  return <span className={`${variants[variant]} ${className}`.trim()}>{children}</span>;
}

export function statusBadge(estado) {
  const map = {
    pendiente: 'pending',
    pagado: 'success',
    parcial: 'info',
    vencido: 'danger',
    anulada: 'rejected',
    emitida: 'success',
    borrador: 'default',
    aceptada: 'accepted',
    rechazada: 'rejected',
    observada: 'observed',
    facturado: 'success',
    activo: 'success',
    inactivo: 'danger',
    trial: 'brand',
  };
  return map[estado] || 'default';
}
