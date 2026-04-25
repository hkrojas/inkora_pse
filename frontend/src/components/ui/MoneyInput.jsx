import { useRef } from 'react';

// Input numérico alineado a la derecha, sin spinners nativos, con prefijo de moneda.
// Acepta valor string o number. Llama onChange(stringValue) en cada cambio.
export default function MoneyInput({
  value,
  onChange,
  moneda = 'PEN',
  placeholder = '0.00',
  disabled = false,
  required = false,
  compact = false,
  onKeyDown,
  inputRef: externalRef,
  style,
  ...rest
}) {
  const internalRef = useRef(null);
  const ref = externalRef || internalRef;
  const symbol = moneda === 'USD' ? '$' : 'S/';
  const minHeight = compact ? '40px' : '44px';

  const handleKeyDown = (e) => {
    // Allow: digits, decimal point/comma, backspace, delete, tab, enter, arrows, home/end
    const allowed = ['Backspace', 'Delete', 'Tab', 'Enter', 'ArrowLeft', 'ArrowRight', 'Home', 'End', '.', ','];
    if (!allowed.includes(e.key) && !/^\d$/.test(e.key) && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
    }
    // Normalize comma to period
    if (e.key === ',') {
      e.preventDefault();
      const el = ref.current;
      const pos = el.selectionStart;
      const next = value.replace(',', '.') || '';
      onChange(next.slice(0, pos) + '.' + next.slice(pos));
    }
    onKeyDown?.(e);
  };

  return (
    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', ...style }}>
      <span style={{
        position: 'absolute',
        left: '10px',
        fontFamily: 'var(--font-mono)',
        fontSize: compact ? '10px' : '11px',
        fontWeight: 700,
        color: 'var(--text-tertiary)',
        pointerEvents: 'none',
        userSelect: 'none',
        lineHeight: 1,
      }}>
        {symbol}
      </span>
      <input
        ref={ref}
        type="text"
        inputMode="decimal"
        required={required}
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        style={{
          width: '100%',
          minHeight,
          paddingLeft: '30px',
          paddingRight: '10px',
          textAlign: 'right',
          fontFamily: 'var(--font-mono)',
          fontSize: compact ? '12px' : '14px',
          fontWeight: 500,
          background: 'var(--bg-surface-2)',
          border: '1.5px solid var(--border-subtle)',
          borderRadius: 0,
          color: disabled ? 'var(--text-tertiary)' : 'var(--text-primary)',
          cursor: disabled ? 'not-allowed' : 'text',
          outline: 'none',
          // Suppress native spinners
          MozAppearance: 'textfield',
          WebkitAppearance: 'none',
          appearance: 'none',
          transition: 'border-color 150ms',
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--brand-600)'; e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--brand-600)'; }}
        onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.boxShadow = 'none'; }}
        {...rest}
      />
    </div>
  );
}
