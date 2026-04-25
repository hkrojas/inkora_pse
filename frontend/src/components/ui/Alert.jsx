import { cn } from '../../lib/utils/cn';
import { Info, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const icons = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  danger: XCircle,
};

const styles = {
  info: 'bg-[var(--color-primary-soft)] text-[var(--color-primary)] border-[var(--color-primary-soft)]',
  success: 'bg-[var(--color-success-soft)] text-[var(--color-success-text)] border-[var(--color-success-soft)]',
  warning: 'bg-[var(--color-warning-soft)] text-[var(--color-warning-text)] border-[var(--color-warning-soft)]',
  danger: 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)] border-[var(--color-danger-soft)]',
};

export default function Alert({ children, variant = 'info', title, className }) {
  const Icon = icons[variant];

  return (
    <div
      role="alert"
      className={cn(
        'flex gap-3 rounded-2xl border p-4',
        styles[variant],
        className
      )}
    >
      <Icon className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        {title && (
          <p className="mb-1 text-sm font-bold">{title}</p>
        )}
        <div className="text-sm leading-relaxed">{children}</div>
      </div>
    </div>
  );
}
