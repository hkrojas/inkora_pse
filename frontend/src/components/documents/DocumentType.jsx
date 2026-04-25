// DocumentTypeBadge — chip visual del tipo de comprobante
// DocumentTypeSwitcher — segmented control prominente Factura / Boleta

const TYPE_CONFIG = {
  '01': { label: 'Factura',       short: 'F',  color: 'var(--brand-600)', bg: 'var(--brand-100)', border: 'var(--brand-200)' },
  '03': { label: 'Boleta',        short: 'B',  color: 'var(--color-info)', bg: 'var(--color-info-bg)', border: 'rgba(3,105,161,0.2)' },
  '07': { label: 'Nota Crédito',  short: 'NC', color: 'var(--color-warning)', bg: 'var(--color-warning-bg)', border: 'rgba(217,119,6,0.2)' },
  '08': { label: 'Nota Débito',   short: 'ND', color: 'var(--color-error)', bg: 'var(--color-error-bg)', border: 'rgba(220,38,38,0.2)' },
  '00': { label: 'Cotización',    short: 'COT',color: 'var(--text-secondary)', bg: 'var(--bg-surface-2)', border: 'var(--border-subtle)' },
  'GR': { label: 'Guía de Remisión', short: 'GR', color: 'var(--brand-700)', bg: 'var(--brand-100)', border: 'var(--brand-200)' },
};

export function getTypeConfig(tipo) {
  return TYPE_CONFIG[tipo] || TYPE_CONFIG['00'];
}

export function DocumentTypeBadge({ tipo, size = 'md' }) {
  const cfg = getTypeConfig(tipo);
  const fontSize = size === 'sm' ? '9px' : '10px';
  const padding  = size === 'sm' ? '2px 6px' : '3px 8px';
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding,
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      color: cfg.color,
      fontFamily: 'var(--font-mono)',
      fontSize,
      fontWeight: 700,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
    }}>
      {cfg.label}
    </span>
  );
}

export function DocumentTypeSwitcher({ value, onChange, options = ['01', '03'] }) {
  return (
    <div style={{
      display: 'inline-flex',
      border: '1.5px solid var(--border-subtle)',
      background: 'var(--bg-surface-2)',
      overflow: 'hidden',
    }}>
      {options.map((tipo) => {
        const cfg = getTypeConfig(tipo);
        const isActive = value === tipo;
        return (
          <button
            key={tipo}
            type="button"
            onClick={() => onChange(tipo)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 24px',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              border: 'none',
              borderRight: '1.5px solid var(--border-subtle)',
              background: isActive ? cfg.color : 'transparent',
              color: isActive ? '#fff' : 'var(--text-tertiary)',
              cursor: 'pointer',
              transition: 'all 150ms',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => {
              if (!isActive) e.currentTarget.style.background = cfg.bg;
            }}
            onMouseLeave={(e) => {
              if (!isActive) e.currentTarget.style.background = 'transparent';
            }}
          >
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '20px',
              height: '20px',
              borderRadius: 0,
              background: isActive ? 'rgba(255,255,255,0.2)' : cfg.bg,
              color: isActive ? '#fff' : cfg.color,
              fontSize: '10px',
              fontWeight: 900,
            }}>
              {cfg.short}
            </span>
            {cfg.label}
          </button>
        );
      })}
    </div>
  );
}
