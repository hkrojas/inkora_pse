// DocumentTypeBadge — chip visual del tipo de comprobante
// DocumentTypeSwitcher — segmented control prominente Factura / Boleta

const TYPE_CONFIG = {
  '01': { label: 'Factura',       short: 'F',  color: '#4F46E5', bg: '#EEF2FF', border: '#C7D2FE' },
  '03': { label: 'Boleta',        short: 'B',  color: '#0284C7', bg: '#E0F2FE', border: '#BAE6FD' },
  '07': { label: 'Nota Crédito',  short: 'NC', color: '#D97706', bg: '#FEF3C7', border: '#FDE68A' },
  '08': { label: 'Nota Débito',   short: 'ND', color: '#DC2626', bg: '#FEE2E2', border: '#FECACA' },
  '00': { label: 'Cotización',    short: 'COT',color: '#475569', bg: '#F1F5F9', border: '#CBD5E1' },
  'GR': { label: 'Guía de Remisión', short: 'GR', color: '#7C3AED', bg: '#F5F3FF', border: '#DDD6FE' },
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
      border: '1.5px solid #E2E8F0',
      background: '#F8FAFC',
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
              borderRight: '1.5px solid #E2E8F0',
              background: isActive ? cfg.color : 'transparent',
              color: isActive ? '#fff' : '#64748B',
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
              borderRadius: '50%',
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
