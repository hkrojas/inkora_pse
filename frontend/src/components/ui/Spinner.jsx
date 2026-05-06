function SpinnerGlyph({ size = 'md', className = '' }) {
  const numericSize = typeof size === 'number' ? size : null;
  const classes = ['spinner'];

  if (size === 'sm') classes.push('spinner--sm');
  if (size === 'lg') classes.push('spinner--lg');

  const style = numericSize
    ? {
        '--spinner-size': `${numericSize}px`,
        '--spinner-border': `${Math.max(2, Math.round(numericSize / 7))}px`,
        width: `${numericSize}px`,
        height: `${numericSize}px`,
      }
    : undefined;

  return <span className={`${classes.join(' ')} ${className}`.trim()} style={style} aria-hidden="true" />;
}

function SpinnerPanel({
  className = '',
  label = 'Cargando',
  hint = 'Preparando datos.',
}) {
  return (
    <div
      className={`spinner-panel-wrapper ${className}`.trim()}
      role="status"
      aria-live="polite"
    >
      <div className="spinner-panel">
        <SpinnerGlyph size="lg" />
        <div className="spinner-panel__copy">
          <p className="spinner-panel__label">{label}</p>
          {hint && <p className="spinner-panel__hint">{hint}</p>}
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
    <div className="spinner-center">
      <Spinner
        size="lg"
        label="Cargando sesion"
        hint="Validando acceso y preparando el entorno de trabajo."
      />
    </div>
  );
}
