const variants = {
  default:  'bg-gray-100 text-gray-700',
  success:  'bg-green-100 text-green-700',
  warning:  'bg-yellow-100 text-yellow-700',
  danger:   'bg-red-100 text-red-700',
  info:     'bg-blue-100 text-blue-700',
  pending:  'bg-orange-100 text-orange-700',
};

export default function Badge({ children, variant = 'default', className = '' }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

export function statusBadge(estado) {
  const map = {
    pendiente: 'warning',
    pagado:    'success',
    parcial:   'info',
    vencido:   'danger',
    anulada:   'danger',
    emitida:   'success',
    borrador:  'default',
  };
  return map[estado] || 'default';
}
