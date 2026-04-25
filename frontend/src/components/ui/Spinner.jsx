function SpinnerGlyph({ size = 'md', className = '' }) {
  const numericSize = typeof size === 'number' ? size : null;
  const classes = ['spinner'];

  if (size === 'sm') classes.push('spinner--sm');
  if (size === 'lg') classes.push('spinner--lg');

  const style = numericSize
    ? {
        '--spinner-size': `${numericSize}px`,
        '--spinner-border': `${Math.max(2, Math.round(numericSize / 7))}px`,
      }
    : undefined;

  return <span className={`${classes.join(' ')} ${className}`.trim()} style={style} aria-hidden="true" />;
}

function SpinnerPanel({
  className = '',
  label = 'Cargando módulo',
  hint = 'Preparando datos...',
}) {
  return (
    <div
      className={className}
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '280px',
        padding: '32px',
      }}
    >
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '20px',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 0,
        padding: '32px 48px',
        minWidth: '260px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
      }}>
        <SpinnerGlyph size={32} />
        <div style={{ textAlign: 'center' }}>
          <p style={{ margin: 0, fontWeight: 700, fontSize: '13px', color: 'var(--text-primary)', letterSpacing: '0.01em' }}>{label}</p>
          {hint && <p style={{ margin: '5px 0 0', fontSize: '11px', color: 'var(--text-tertiary)' }}>{hint}</p>}
        </div>
        <div style={{ width: '100%', height: '2px', background: 'var(--border-subtle)', borderRadius: 0, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: '40%',
            background: 'var(--brand-600)',
            borderRadius: '2px',
            animation: 'spinner-bar-slide 1.4s ease-in-out infinite',
          }} />
        </div>
      </div>
    </div>
  );
}

export default function Spinner({
  size = 'md',
  className = '',
  label,
  hint,
}) {
  if (size === 'lg') {
    return <SpinnerPanel className={className} label={label} hint={hint} />;
  }

  return <SpinnerGlyph size={size} className={className} />;
}

export function FullPageSpinner() {
  return (
    <div className="spinner-center" style={{ minHeight: '60vh' }}>
      <Spinner
        size="lg"
        label="Cargando sesion"
        hint="Validando acceso y preparando el entorno de trabajo."
      />
    </div>
  );
}
