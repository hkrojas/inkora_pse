/**
 * ProductLineCell — inline product search + new-product creation for line rows.
 *
 * Renders two coordinated inputs: [Código] [Descripción/Nombre]
 * Both search the catalog in real time. Selecting a match fills the item.
 * When nothing matches, marks item._isNew = true so the parent can create
 * the product on save.
 *
 * Props:
 *   value        — full line-item object: { producto_id, codigo, descripcion, precio_unitario,
 *                  unidad_medida, tipo_afectacion_igv, _isNew }
 *   onChange     — (nextItem) => void  (replaces full item)
 *   products     — catalog array from API
 *   incluyeIgv   — boolean, used to display catalog price in dropdown
 *   sym          — currency symbol ('S/' | '$')
 *   onGenerateCode — async () => string  (hits /productos/codigo-sugerido)
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { RotateCw, X } from 'lucide-react';

const NARROW = '90px'; // code input fixed width

function formatPrice(product, incluyeIgv, sym) {
  const amount = incluyeIgv
    ? Number(product.precio_unitario || 0)
    : Number(product.valor_unitario || product.precio_unitario || 0);
  return `${sym} ${amount.toFixed(2)}`;
}

export default function ProductLineCell({
  value,
  onChange,
  products = [],
  incluyeIgv = true,
  sym = 'S/',
  onGenerateCode,
}) {
  const [activeInput, setActiveInput]   = useState(null); // 'codigo' | 'nombre'
  const [pos, setPos]                   = useState({ top: 0, left: 0, width: 0 });
  const [generating, setGenerating]     = useState(false);

  const containerRef = useRef(null);
  const dropdownRef  = useRef(null);
  const codigoRef    = useRef(null);
  const nombreRef    = useRef(null);

  const isExisting = !!value.producto_id && !value._isNew;
  const isNew      = value._isNew;

  // Build filtered list based on which input is active
  const dropdownItems = activeInput ? products.filter((p) => {
    const q = (activeInput === 'codigo' ? value.codigo : value.descripcion).toLowerCase();
    if (!q) return false;
    return activeInput === 'codigo'
      ? (p.codigo_interno || '').toLowerCase().includes(q)
      : (p.nombre || '').toLowerCase().includes(q);
  }).slice(0, 10) : [];

  // Update dropdown position (anchored to container)
  const openFor = useCallback((field) => {
    if (!containerRef.current) return;
    const r = containerRef.current.getBoundingClientRect();
    setPos({
      top:   r.bottom + window.scrollY + 3,
      left:  r.left   + window.scrollX,
      width: Math.max(r.width, 360),
    });
    setActiveInput(field);
  }, []);

  // Close on outside click
  useEffect(() => {
    if (!activeInput) return;
    const handle = (e) => {
      if (!containerRef.current?.contains(e.target) && !dropdownRef.current?.contains(e.target)) {
        setActiveInput(null);
        // If name filled but no product selected → mark as new
        if (!value.producto_id && value.descripcion.trim()) {
          onChange({ ...value, _isNew: true });
        }
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [activeInput, value, onChange]);

  const handleSelectProduct = (product) => {
    const price = incluyeIgv
      ? Number(product.precio_unitario || 0)
      : Number(product.valor_unitario || product.precio_unitario || 0);
    onChange({
      ...value,
      producto_id:         String(product.id),
      codigo:              product.codigo_interno || '',
      descripcion:         product.nombre || '',
      precio_unitario:     price ? price.toFixed(2) : value.precio_unitario,
      unidad_medida:       product.unidad_medida || value.unidad_medida || 'NIU',
      tipo_afectacion_igv: product.tipo_afectacion_igv || value.tipo_afectacion_igv || '10',
      _isNew:              false,
    });
    setActiveInput(null);
  };

  const handleClear = () => {
    onChange({ ...value, producto_id: '', codigo: '', descripcion: '', _isNew: false });
    setActiveInput(null);
    setTimeout(() => codigoRef.current?.focus(), 0);
  };

  const handleCodigoChange = (e) => {
    const v = e.target.value;
    onChange({ ...value, codigo: v, producto_id: '', _isNew: false });
    openFor('codigo');
  };

  const handleNombreChange = (e) => {
    const v = e.target.value;
    onChange({ ...value, descripcion: v, producto_id: '', _isNew: false });
    openFor('nombre');
  };

  const handleGenerateCode = async () => {
    if (!onGenerateCode) return;
    setGenerating(true);
    try {
      const code = await onGenerateCode();
      onChange({ ...value, codigo: code });
    } catch {
      // silent
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '5px', minWidth: 0 }}>

      {/* ── Código input ── */}
      <input
        ref={codigoRef}
        readOnly={isExisting}
        placeholder="Código"
        value={value.codigo}
        onChange={handleCodigoChange}
        onFocus={() => { if (!isExisting) openFor('codigo'); }}
        style={{
          width: NARROW,
          flexShrink: 0,
          height: '36px',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          fontWeight: 700,
          letterSpacing: '0.04em',
          padding: '0 8px',
          border: `1.5px solid ${isNew && !value.codigo ? 'var(--color-warning)' : isExisting ? 'var(--border-subtle)' : 'var(--border-subtle)'}`,
          background: isExisting ? 'var(--bg-surface-2)' : 'var(--bg-surface)',
          color: isExisting ? 'var(--text-tertiary)' : 'var(--text-primary)',
          outline: 'none',
          boxSizing: 'border-box',
          textTransform: 'uppercase',
        }}
      />

      {/* ── Nombre / Descripción input ── */}
      <input
        ref={nombreRef}
        placeholder={isExisting ? '' : 'Producto o descripción...'}
        value={value.descripcion}
        onChange={isExisting ? (e) => onChange({ ...value, descripcion: e.target.value }) : handleNombreChange}
        onFocus={() => { if (!isExisting) openFor('nombre'); }}
        style={{
          flex: 1,
          minWidth: 0,
          height: '36px',
          fontFamily: 'var(--font-body)',
          fontSize: '13px',
          padding: '0 8px',
          border: `1.5px solid ${isExisting ? 'var(--border-subtle)' : 'var(--border-subtle)'}`,
          background: 'var(--bg-surface)',
          color: 'var(--text-primary)',
          outline: 'none',
          boxSizing: 'border-box',
        }}
      />

      {/* ── Right action buttons ── */}
      {isExisting && (
        <button
          type="button"
          onClick={handleClear}
          title="Quitar producto"
          style={{ flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', display: 'flex', padding: '4px', lineHeight: 1 }}
        >
          <X size={12} />
        </button>
      )}

      {isNew && !value.codigo && onGenerateCode && (
        <button
          type="button"
          onClick={handleGenerateCode}
          disabled={generating}
          title="Generar código automático"
          style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: '3px', padding: '0 8px', height: '28px', background: 'var(--color-warning-bg)', border: '1px solid rgba(217,119,6,0.2)', color: 'var(--color-warning)', fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700, cursor: generating ? 'wait' : 'pointer', whiteSpace: 'nowrap', letterSpacing: '0.06em', textTransform: 'uppercase' }}
        >
          <RotateCw size={10} style={generating ? { animation: 'spin 1s linear infinite' } : {}} />
          {generating ? '...' : 'Código'}
        </button>
      )}

      {/* ── New-product indicator ── */}
      {isNew && value.descripcion && (
        <span style={{ flexShrink: 0, fontSize: '9px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-warning)', background: 'var(--color-warning-bg)', border: '1px solid rgba(217,119,6,0.2)', padding: '2px 6px', letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
          Nuevo
        </span>
      )}

      {/* ── Dropdown portal ── */}
      {activeInput && dropdownItems.length > 0 && createPortal(
        <div
          ref={dropdownRef}
          style={{ position: 'absolute', top: pos.top, left: pos.left, width: pos.width, background: 'var(--bg-surface)', border: '1.5px solid var(--brand-200)', boxShadow: 'var(--shadow-brut-md)', zIndex: 9999, maxHeight: '240px', overflowY: 'auto' }}
        >
          {dropdownItems.map((p) => (
            <button
              key={p.id}
              type="button"
              onMouseDown={(e) => { e.preventDefault(); handleSelectProduct(p); }}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '8px 14px', border: 'none', borderBottom: '1px solid var(--border-hair)', background: 'var(--bg-surface)', cursor: 'pointer', textAlign: 'left', gap: '12px' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-surface-2)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-surface)'; }}
            >
              <div style={{ minWidth: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, color: 'var(--brand-600)', flexShrink: 0, minWidth: '68px' }}>
                  {p.codigo_interno || '—'}
                </span>
                <span style={{ fontSize: '13px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {p.nombre}
                </span>
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', flexShrink: 0 }}>
                {formatPrice(p, incluyeIgv, sym)}
              </span>
            </button>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
}
