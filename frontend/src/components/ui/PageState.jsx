import { AlertTriangle, RefreshCw } from 'lucide-react';
import EmptyState from './EmptyState';
import Spinner from './Spinner';

export function PageLoading({ title = 'Cargando', description = 'Preparando datos.' }) {
  return (
    <div className="page-state page-state--loading" role="status" aria-live="polite">
      <Spinner size="lg" />
      <div>
        <p className="page-state__title">{title}</p>
        <p className="page-state__description">{description}</p>
      </div>
    </div>
  );
}

export function PageError({
  title = 'No se pudo cargar la información',
  description,
  error,
  onRetry,
}) {
  const message = description || error?.message || 'Revisa la conexión con el backend e inténtalo nuevamente.';

  return (
    <EmptyState
      icon={<AlertTriangle size={24} />}
      title={title}
      description={message}
      actionLabel={onRetry ? 'Reintentar' : undefined}
      onAction={onRetry}
    />
  );
}

export function InlineRetry({ children = 'Reintentar', onClick, loading = false }) {
  return (
    <button type="button" className="btn" onClick={onClick} disabled={loading}>
      {loading ? <Spinner size="sm" /> : <RefreshCw size={15} />}
      {children}
    </button>
  );
}
