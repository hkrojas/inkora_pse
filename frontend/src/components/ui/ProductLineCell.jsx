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
import { Loader2, RotateCw, X } from 'lucide-react';
import { productos as productosSvc } from '../../services/productos';

const NARROW = '90px'; // code input fixed width
const SEARCH_DEBOUNCE_MS = 250;
const SEARCH_MIN_CHARS = 2;
const SEARCH_LIMIT = 20;

function productKey(product) {
  if (product?.id !== undefined && product?.id !== null) return `id:${product.id}`;
  return `product:${product?.codigo_interno || ''}:${product?.nombre || ''}`;
}

function mergeProducts(...groups) {
  const seen = new Set();
  const merged = [];
  groups.flat().forEach((product) => {
    const key = productKey(product);
    if (seen.has(key)) return;
    seen.add(key);
    merged.push(product);
  });
  return merged;
}

function productMatchesQuery(product, query) {
  const normalizedQuery = String(query || '').trim().toLowerCase();
  if (!normalizedQuery) return false;
  return [
    product?.codigo_interno,
    product?.nombre,
    product?.descripcion,
  ].some((value) => String(value || '').toLowerCase().includes(normalizedQuery));
}

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
  const [remoteProducts, setRemoteProducts] = useState([]);
  const [searchingProducts, setSearchingProducts] = useState(false);
  const [searchedQuery, setSearchedQuery] = useState('');

  const containerRef = useRef(null);
  const dropdownRef  = useRef(null);
  const codigoRef    = useRef(null);
  const nombreRef    = useRef(null);
  const searchCacheRef = useRef(new Map());
  const searchAbortRef = useRef(null);

  const isExisting = !!value.producto_id && !value._isNew;
  const isNew      = value._isNew;

  const activeQuery = activeInput === 'codigo' ? value.codigo : value.descripcion;

  const matchedProducts = useCallback((query, source = products) => {
    const q = String(query || '').toLowerCase().trim();
    if (!q) return [];
    return source.filter((p) => productMatchesQuery(p, q));
  }, [products]);

  useEffect(() => {
    if (!activeInput || isExisting) {
      searchAbortRef.current?.abort();
      setRemoteProducts([]);
      setSearchingProducts(false);
      setSearchedQuery('');
      return undefined;
    }

    const query = String(activeQuery || '').trim();
    if (query.length < SEARCH_MIN_CHARS) {
      searchAbortRef.current?.abort();
      setRemoteProducts([]);
      setSearchingProducts(false);
      setSearchedQuery('');
      return undefined;
    }

    const cacheKey = query.toLowerCase();
    const cached = searchCacheRef.current.get(cacheKey);
    if (cached) {
      setRemoteProducts(cached);
      setSearchingProducts(false);
      setSearchedQuery(query);
      return undefined;
    }

    setRemoteProducts([]);
    setSearchingProducts(true);
    setSearchedQuery('');
    searchAbortRef.current?.abort();
    const controller = new AbortController();
    searchAbortRef.current = controller;

    const timerId = setTimeout(() => {
      productosSvc.search(query, SEARCH_LIMIT, { signal: controller.signal })
        .then((items) => {
          const results = Array.isArray(items) ? items : [];
          searchCacheRef.current.set(cacheKey, results);
          if (!controller.signal.aborted) {
            setRemoteProducts(results);
            setSearchedQuery(query);
          }
        })
        .catch((error) => {
          if (!error?.isCanceled && !controller.signal.aborted) {
            setRemoteProducts([]);
            setSearchedQuery(query);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setSearchingProducts(false);
          if (searchAbortRef.current === controller) searchAbortRef.current = null;
        });
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      clearTimeout(timerId);
      controller.abort();
    };
  }, [activeInput, activeQuery, isExisting]);

  const currentSearchQuery = String(activeQuery || '').trim();
  const remoteResultsMatchCurrentQuery = searchedQuery.trim().toLowerCase() === currentSearchQuery.toLowerCase();
  const dropdownItems = activeInput
    ? mergeProducts(
      remoteResultsMatchCurrentQuery ? remoteProducts : [],
      matchedProducts(activeQuery, products),
    ).slice(0, 10)
    : [];
  const canShowSearchMenu = activeInput && !isExisting && currentSearchQuery.length >= SEARCH_MIN_CHARS;
  const showNoSearchResults = canShowSearchMenu
    && !searchingProducts
    && remoteResultsMatchCurrentQuery
    && dropdownItems.length === 0;

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
    setRemoteProducts((current) => mergeProducts([product], current));
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
    setRemoteProducts([]);
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
      {canShowSearchMenu && createPortal(
        <div
          ref={dropdownRef}
          className="ink-combobox-menu dropdown-enter"
          style={{ top: pos.top, left: pos.left, width: pos.width }}
        >
          {searchingProducts && (
            <div className="ink-combobox-feedback">
              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
              Buscando productos...
            </div>
          )}
          {showNoSearchResults && (
            <div className="ink-combobox-feedback ink-combobox-feedback--empty">
              No hay productos registrados con ese codigo o nombre.
            </div>
          )}
          {dropdownItems.map((p) => (
            <button
              key={p.id}
              type="button"
              onMouseDown={(e) => { e.preventDefault(); handleSelectProduct(p); }}
              className="ink-combobox-option"
            >
              <div className="ink-combobox-option-copy ink-product-option-copy">
                <span className="ink-product-option-code">
                  {p.codigo_interno || '-'}
                </span>
                <span className="ink-combobox-option-title ink-product-option-title">
                  {p.nombre}
                </span>
              </div>
              <span className="ink-combobox-pill">
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
