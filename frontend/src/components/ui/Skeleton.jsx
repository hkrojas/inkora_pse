export function Skeleton({ className = '', style, children }) {
  return (
    <div
      className={`skeleton ${className}`.trim()}
      style={style}
      aria-hidden="true"
    >
      {children}
    </div>
  );
}

export function SkeletonText({ lines = 3, className = '' }) {
  return (
    <div className={className} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton skeleton--text"
          style={i === lines - 1 ? { width: '75%', marginBottom: 0 } : undefined}
        />
      ))}
    </div>
  );
}

export function SkeletonRow({ cells = 4, className = '' }) {
  return (
    <div className={`skeleton-row ${className}`.trim()} aria-hidden="true">
      <Skeleton className="skeleton--circle" style={{ width: 32, height: 32 }} />
      {Array.from({ length: cells - 1 }).map((_, i) => (
        <div
          key={i}
          className={`skeleton skeleton-row__cell ${
            i === 0 ? 'skeleton-row__cell--lg' : i === cells - 2 ? 'skeleton-row__cell--sm' : ''
          }`.trim()}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`skeleton-card ${className}`.trim()} aria-hidden="true">
      <Skeleton className="skeleton--title" />
      <SkeletonText lines={3} />
    </div>
  );
}

export function SkeletonForm({ fields = 4, className = '' }) {
  return (
    <div className={`skeleton-form ${className}`.trim()} aria-hidden="true">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="skeleton-form__field">
          <Skeleton className="skeleton-form__label" />
          <Skeleton className="skeleton-form__input" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, className = '' }) {
  return (
    <div className={`flex flex-col gap-2 ${className}`.trim()} aria-hidden="true">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  );
}
