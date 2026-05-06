const TYPE_CONFIG = {
  '01': { label: 'Factura', short: 'F', tone: 'primary' },
  '03': { label: 'Boleta', short: 'B', tone: 'info' },
  '07': { label: 'Nota crédito', short: 'NC', tone: 'warning' },
  '08': { label: 'Nota débito', short: 'ND', tone: 'danger' },
  '00': { label: 'Cotización', short: 'COT', tone: 'neutral' },
  GR: { label: 'Guía de remisión', short: 'GR', tone: 'primary' },
};

export function getTypeConfig(tipo) {
  return TYPE_CONFIG[tipo] || TYPE_CONFIG['00'];
}

export function DocumentTypeBadge({ tipo, size = 'md' }) {
  const cfg = getTypeConfig(tipo);
  return (
    <span className={`document-type-badge document-type-badge--${cfg.tone} document-type-badge--${size}`}>
      <span className="document-type-badge__key">{cfg.short}</span>
      {cfg.label}
    </span>
  );
}

export function DocumentTypeSwitcher({ value, onChange, options = ['01', '03'] }) {
  return (
    <div className="document-type-switcher" role="tablist" aria-label="Tipo de comprobante">
      {options.map((tipo) => {
        const cfg = getTypeConfig(tipo);
        const isActive = value === tipo;
        return (
          <button
            key={tipo}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={`document-type-option document-type-option--${cfg.tone}${isActive ? ' is-active' : ''}`}
            onClick={() => onChange(tipo)}
          >
            <span className="document-type-option__key">{cfg.short}</span>
            <span>{cfg.label}</span>
          </button>
        );
      })}
    </div>
  );
}
