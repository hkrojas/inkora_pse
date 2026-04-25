import { useEffect, useRef, useState, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, Eye, FileUp, Mail, Plus, Trash2,
} from 'lucide-react';
import { clientes as clientesSvc } from '../services/clientes';
import { productos as productosSvc } from '../services/productos';
import { cotizaciones as cotizacionesSvc } from '../services/cotizaciones';
import { tenant as tenantSvc } from '../services/tenant';
import FiscalDocPreview from '../components/documents/FiscalDocPreview';
import ClientCombobox from '../components/ui/ClientCombobox';
import ProductLineCell from '../components/ui/ProductLineCell';
import { upsertCliente, upsertProductos } from '../lib/utils/upsert';
import Spinner from '../components/ui/Spinner';
import Modal from '../components/ui/Modal';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import { FieldError } from '../components/ui/FieldError';
import { DocumentTypeSwitcher } from '../components/documents/DocumentType';
import ConfirmEmitDialog from '../components/documents/ConfirmEmitDialog';
import { useToast } from '../components/ui/Toast';
import {
  IGV_FACTOR, PAYMENT_OPTIONS, MEDIO_PAGO_OPTIONS, OPERATION_OPTIONS, UNIT_OPTIONS,
  inputDateToday, addDays, paymentDays, toApiDate,
  formatCurrency, deriveSeries, computeLine, computeDocumentTotals,
} from '../lib/utils/documents';
import { useFieldValidation, rules } from '../lib/utils/useFieldValidation';

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_ITEM = () => ({
  key: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  producto_id: '',
  codigo: '',
  descripcion: '',
  unidad_medida: 'NIU',
  cantidad: '1',
  precio_unitario: '',
  tipo_afectacion_igv: '10',
  _isNew: false,
});

function createInitialForm(initialType) {
  const tipo = initialType === '03' ? '03' : '01';
  return {
    tipo_comprobante: tipo,
    modo_emision: 'cpe',
    moneda: 'PEN',
    tipo_operacion: '0101',
    condicion_pago: 'contado',
    medio_pago: 'Efectivo',
    fecha_emision: inputDateToday(),
    fecha_vencimiento: '',
    observaciones: '',
    incluye_igv: true,
    enviar_correo: false,
    cliente_id: '',
    cliente: {
      tipo_documento: '6',
      numero_documento: '',
      razon_social: '',
      direccion: '',
      email: '',
      telefono: '',
    },
    items: [EMPTY_ITEM()],
  };
}

// ─── Validation rules ─────────────────────────────────────────────────────────

function buildValidationRules(form) {
  return {
    razon_social:      rules.required('Nombre / Razón social'),
    numero_documento:  (v) => {
      const s = String(v || '').trim();
      if (!s) return 'Número de documento es obligatorio';
      if (form.tipo_comprobante === '01') {
        if (!/^\d{11}$/.test(s)) return 'Factura requiere RUC (11 dígitos)';
      } else if (form.cliente.tipo_documento === '1' && s.length !== 8) {
        return 'DNI debe tener 8 dígitos';
      }
      return null;
    },
    items: (v) => {
      const valid = (form.items || []).some(
        (it) => it.descripcion.trim() && Number(it.cantidad) > 0 && Number(it.precio_unitario) > 0,
      );
      return valid ? null : 'Agrega al menos una línea con descripción, cantidad y precio';
    },
  };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionCard({ kicker, title, children, aside, accent }) {
  const borderColor = accent || 'transparent';
  return (
    <section className="comprobante-section" style={{ borderTop: `3px solid ${borderColor}` }}>
      <div className="comprobante-section-header">
        <div>
          <p className="comprobante-section-kicker">{kicker}</p>
          <h3 className="comprobante-section-title">{title}</h3>
        </div>
        {aside && <div className="comprobante-section-aside">{aside}</div>}
      </div>
      {children}
    </section>
  );
}

function ModeSwitch({ mode, onChange }) {
  return (
    <div className="comprobante-mode-switch">
      <button type="button" className={`comprobante-mode-option${mode === 'cpe' ? ' is-active' : ''}`} onClick={() => onChange('cpe')}>CPE</button>
      <button type="button" className={`comprobante-mode-option${mode === 'contingencia' ? ' is-active' : ''}`} onClick={() => onChange('contingencia')}>Contingencia</button>
    </div>
  );
}

function BuilderSwitch({ label, checked, onChange, accent = 'brand' }) {
  return (
    <button
      type="button"
      className={`comprobante-toggle${checked ? ` comprobante-toggle--${accent} is-active` : ''}`}
      onClick={() => onChange(!checked)}
    >
      <span className="comprobante-toggle-track"><span className="comprobante-toggle-thumb" /></span>
      <span className="comprobante-toggle-label">{label}</span>
    </button>
  );
}

function PreviewModal({ open, onClose, form, totals, tenantData }) {
  const series  = deriveSeries(form.tipo_comprobante, form.modo_emision);
  const tipoLabel = form.tipo_comprobante === '01' ? 'FACTURA' : 'BOLETA DE VENTA';
  const tipoDocLabel = form.cliente.tipo_documento === '6' ? 'RUC' : form.cliente.tipo_documento === '1' ? 'DNI' : 'DOC';
  const condPagoLabel = PAYMENT_OPTIONS.find((o) => o.value === form.condicion_pago)?.label?.toUpperCase() || 'CONTADO';
  const monedaTexto = form.moneda === 'USD' ? 'DÓLARES' : 'SOLES';

  const fmtDate = (iso) => {
    if (!iso) return '';
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
  };

  const fiscalItems = form.items
    .filter((it) => it.descripcion.trim() && Number(it.cantidad) > 0 && Number(it.precio_unitario) > 0)
    .map((it) => {
      const line = computeLine(it, form.incluye_igv);
      return {
        codigo:         it.codigo || '',
        descripcion:    it.descripcion,
        unidad:         it.unidad_medida || 'NIU',
        cantidad:       line.cantidad,
        valorUnitario:  line.unitBase,
        precioUnitario: line.unitFinal,
        descuento:      0,
        valorVenta:     line.subtotal,
      };
    });

  const company = {
    name:    tenantData?.business_name    || '—',
    ruc:     tenantData?.business_ruc     || '—',
    address: tenantData?.business_address || '—',
    phone:   tenantData?.business_phone   || '',
    email:   tenantData?.business_email   || '',
  };

  return (
    <Modal open={open} onClose={onClose} title={`Vista previa — ${tipoLabel} ${series}-XXXXXX`} size="xl">
      <div style={{ overflow: 'auto', maxHeight: '75vh' }}>
        <FiscalDocPreview
          accentColor={tenantData?.primary_color || '#004AAD'}
          company={company}
          client={{
            razon_social:          form.cliente.razon_social || '—',
            tipo_documento_label:  tipoDocLabel,
            numero_documento:      form.cliente.numero_documento || '—',
            direccion:             form.cliente.direccion || '—',
          }}
          docInfo={{
            tipoLabel,
            serie:                series,
            numero:               'XXXXXX',
            fecha_emision:        fmtDate(form.fecha_emision),
            fecha_vencimiento:    fmtDate(form.fecha_vencimiento),
            moneda_texto:         monedaTexto,
            condicion_pago_label: condPagoLabel,
            medio_pago:           (form.medio_pago || 'EFECTIVO').toUpperCase(),
            observaciones:        form.observaciones || '',
          }}
          items={fiscalItems}
          totals={totals}
          bankAccounts={tenantData?.bank_accounts}
        />
      </div>
    </Modal>
  );
}

// ─── Line row ─────────────────────────────────────────────────────────────────

function LineRow({ item, index, moneda, incluyeIgv, products, isLast, onItemChange, onFieldChange, onRemove, onAddNext }) {
  const priceRef = useRef(null);
  const line = computeLine(item, incluyeIgv);
  const sym = moneda === 'USD' ? '$' : 'S/';

  const handlePriceKeyDown = (e) => {
    if (e.key === 'Tab' && !e.shiftKey && isLast) {
      e.preventDefault();
      onAddNext();
    }
  };

  const handleGenerateCode = async () => {
    try {
      const data = await productosSvc.generateCode();
      return data.codigo;
    } catch {
      return '';
    }
  };

  return (
    <div className="comprobante-line-row" style={{ gridTemplateColumns: '3fr 0.8fr 0.9fr 1fr 1fr 0.65fr' }}>
      {/* Product + description (merged into ProductLineCell) */}
      <div style={{ minWidth: 0 }}>
        <ProductLineCell
          value={item}
          onChange={(next) => onItemChange(index, next)}
          products={products}
          incluyeIgv={incluyeIgv}
          sym={sym}
          onGenerateCode={handleGenerateCode}
        />
      </div>

      {/* Unit */}
      <CustomSelect
        value={item.unidad_medida}
        onChange={(v) => onFieldChange(index, 'unidad_medida', v)}
        options={UNIT_OPTIONS}
        compact
      />

      {/* Quantity */}
      <input
        type="text"
        inputMode="decimal"
        className="input"
        value={item.cantidad}
        onChange={(e) => onFieldChange(index, 'cantidad', e.target.value)}
        style={{ minHeight: '40px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, MozAppearance: 'textfield', WebkitAppearance: 'none', appearance: 'none' }}
        required
      />

      {/* Unit price */}
      <div style={{ position: 'relative' }}>
        <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, color: 'var(--text-tertiary)', pointerEvents: 'none' }}>{sym}</span>
        <input
          ref={priceRef}
          type="text"
          inputMode="decimal"
          className="input"
          value={item.precio_unitario}
          onChange={(e) => onFieldChange(index, 'precio_unitario', e.target.value)}
          onKeyDown={handlePriceKeyDown}
          style={{ minHeight: '40px', paddingLeft: '26px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, MozAppearance: 'textfield', WebkitAppearance: 'none', appearance: 'none' }}
          placeholder="0.00"
          required
        />
      </div>

      {/* Total (readonly) */}
      <div className="comprobante-readonly" style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
        <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginRight: '2px' }}>{sym}</span>
        {Number(line.total).toLocaleString('es-PE', { minimumFractionDigits: 2 })}
      </div>

      {/* Remove */}
      <button
        type="button"
        className="btn-ghost"
        onClick={() => onRemove(index)}
        style={{ color: 'var(--text-tertiary)', padding: '6px' }}
        onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-error)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-tertiary)'; }}
      >
        <Trash2 size={14} />
      </button>
    </div>
  );
}

// ─── Validation summary ───────────────────────────────────────────────────────

function ValidationSummary({ errors }) {
  const msgs = Object.values(errors).filter(Boolean);
  if (!msgs.length) return null;
  return (
    <div style={{
      padding: '10px 14px',
      background: 'var(--color-error-bg)',
      border: '1.5px solid rgba(220,38,38,0.2)',
      marginTop: '10px',
    }}>
      <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-error)', marginBottom: '4px' }}>Faltan datos para emitir:</p>
      <ul style={{ margin: 0, padding: '0 0 0 14px' }}>
        {msgs.map((m, i) => (
          <li key={i} style={{ fontSize: '11px', color: 'var(--color-error)', lineHeight: 1.6 }}>{m}</li>
        ))}
      </ul>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ComprobanteNuevoPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialType = searchParams.get('tipo') || '01';

  const [form, setForm] = useState(() => createInitialForm(initialType));
  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [tenantData, setTenantData] = useState(null);
  const [loadingData, setLoadingData] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [igvConfirmOpen, setIgvConfirmOpen] = useState(false);
  const [pendingIgv, setPendingIgv] = useState(null);
  const [clienteState, setClienteState] = useState({ isDirty: false, isNew: false });
  const fileRef = useRef(null);

  const { errors, validate, clearField } = useFieldValidation(buildValidationRules(form));

  useEffect(() => {
    setForm(createInitialForm(initialType));
    setClienteState({ isDirty: false, isNew: false });
  }, [initialType]);

  useEffect(() => {
    Promise.all([clientesSvc.list(), productosSvc.list(), tenantSvc.get()])
      .then(([c, p, t]) => {
        setClientes(Array.isArray(c) ? c : []);
        setProductos(Array.isArray(p) ? p : []);
        setTenantData(t || null);
      })
      .catch(() => toast('No se pudo cargar el catálogo base del comprobante', 'error'))
      .finally(() => setLoadingData(false));
  }, [toast]);

  const seriesPreview = deriveSeries(form.tipo_comprobante, form.modo_emision);
  const totals = computeDocumentTotals(form.items, form.incluye_igv);
  const backTarget = form.tipo_comprobante === '01' ? '/facturas' : '/boletas';
  const tipoLabel = form.tipo_comprobante === '01' ? 'Factura' : 'Boleta de venta';

  // ─── State setters ───────────────────────────────────────────────────────

  const setRootField = useCallback((key, value) => {
    setForm((cur) => {
      if (key === 'condicion_pago') {
        const days = paymentDays(value);
        return { ...cur, condicion_pago: value, fecha_vencimiento: days > 0 ? addDays(cur.fecha_emision, days) : '' };
      }
      if (key === 'fecha_emision') {
        const days = paymentDays(cur.condicion_pago);
        return { ...cur, fecha_emision: value, fecha_vencimiento: days > 0 ? addDays(value, days) : cur.fecha_vencimiento };
      }
      if (key === 'tipo_comprobante') {
        return {
          ...cur,
          tipo_comprobante: value,
          tipo_operacion: '0101',
        };
      }
      return { ...cur, [key]: value };
    });
  }, []);

  const handleClientFormChange = useCallback((formData, { isDirty, isNew }) => {
    setForm((cur) => ({ ...cur, cliente: { ...cur.cliente, ...formData } }));
    setClienteState({ isDirty, isNew });
    clearField('razon_social');
    clearField('numero_documento');
  }, [clearField]);

  const setItemField = useCallback((index, key, value) => {
    setForm((cur) => ({
      ...cur,
      items: cur.items.map((it, i) => i === index ? { ...it, [key]: value } : it),
    }));
  }, []);

  const handleItemChange = useCallback((index, next) => {
    setForm((cur) => ({
      ...cur,
      items: cur.items.map((it, i) => i === index ? { ...it, ...next } : it),
    }));
  }, []);

  const addItem = useCallback(() => {
    setForm((cur) => ({ ...cur, items: [...cur.items, EMPTY_ITEM()] }));
  }, []);

  const removeItem = useCallback((index) => {
    setForm((cur) => ({
      ...cur,
      items: cur.items.length === 1 ? cur.items : cur.items.filter((_, i) => i !== index),
    }));
  }, []);

  // IGV toggle with confirmation when prices exist
  const handleIgvToggle = (newVal) => {
    const hasPrices = form.items.some((it) => Number(it.precio_unitario) > 0);
    if (hasPrices) {
      setPendingIgv(newVal);
      setIgvConfirmOpen(true);
    } else {
      applyIgvToggle(newVal);
    }
  };

  const applyIgvToggle = (newVal) => {
    setForm((cur) => ({
      ...cur,
      incluye_igv: newVal,
      items: cur.items.map((it) => {
        const amount = Number(it.precio_unitario || 0);
        if (!amount) return it;
        const converted = newVal ? amount * IGV_FACTOR : amount / IGV_FACTOR;
        return { ...it, precio_unitario: converted.toFixed(2) };
      }),
    }));
  };

  // CSV import
  const handleImportCsv = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const hasData = form.items.some((it) => it.descripcion.trim());
    if (hasData) {
      const ok = window.confirm(`Vas a reemplazar ${form.items.length} línea(s) con el contenido del CSV. ¿Sí, reemplazar?`);
      if (!ok) { event.target.value = ''; return; }
    }
    try {
      const text = await file.text();
      const [headerLine, ...lines] = text.split(/\r?\n/).filter(Boolean);
      const headers = headerLine.split(',').map((v) => v.trim().toLowerCase());
      const imported = lines
        .map((line) => {
          const values = line.split(',');
          const row = Object.fromEntries(headers.map((h, i) => [h, (values[i] || '').trim()]));
          return { ...EMPTY_ITEM(), codigo: row.codigo || '', descripcion: row.descripcion || row.detalle || '', unidad_medida: row.unidad_medida || row.unidad || 'NIU', cantidad: row.cantidad || '1', precio_unitario: row.precio_unitario || row.precio || '' };
        })
        .filter((it) => it.descripcion);
      if (!imported.length) { toast('El archivo no contiene líneas válidas', 'error'); return; }
      setForm((cur) => ({ ...cur, items: imported }));
      toast(`Se importaron ${imported.length} líneas desde CSV`);
    } catch {
      toast('No se pudo leer el archivo CSV', 'error');
    } finally {
      event.target.value = '';
    }
  };

  // ─── Validate & open confirm ─────────────────────────────────────────────

  const handleEmitClick = () => {
    const values = {
      razon_social: form.cliente.razon_social,
      numero_documento: form.cliente.numero_documento,
      cliente_tipo_documento: form.cliente.tipo_documento,
      tipo_comprobante: form.tipo_comprobante,
      items: form.items,
    };
    const ok = validate(values);
    if (!ok) return;
    setConfirmOpen(true);
  };

  // ─── Actual emission ─────────────────────────────────────────────────────

  const buildQuotePayload = (clienteId, resolvedItems = null) => {
    const srcItems = resolvedItems || form.items;
    return {
      cliente_id: Number(clienteId),
      fecha_vencimiento: form.condicion_pago === 'contado' ? null : toApiDate(form.fecha_vencimiento),
      moneda: form.moneda,
      tipo_comprobante: form.tipo_comprobante,
      observaciones: form.observaciones || null,
      condicion_pago: form.condicion_pago,
      items: srcItems
        .filter((it) => it.descripcion.trim() && Number(it.cantidad) > 0 && Number(it.precio_unitario) > 0)
        .map((it) => ({
          producto_id: it.producto_id ? Number(it.producto_id) : null,
          descripcion: it.descripcion.trim(),
          cantidad: Number(it.cantidad),
          precio_unitario: Number((form.incluye_igv ? Number(it.precio_unitario) : Number(it.precio_unitario) * IGV_FACTOR).toFixed(2)),
          unidad_medida: it.unidad_medida || 'NIU',
          tipo_afectacion_igv: it.tipo_afectacion_igv || '10',
        })),
    };
  };

  const handleEmitConfirmed = async () => {
    setSaving(true);
    try {
      const clienteId = await upsertCliente({
        id: form.cliente_id,
        isNew: clienteState.isNew,
        isDirty: clienteState.isDirty,
        form: form.cliente,
      });
      // Upsert new products before consuming the correlativo
      const resolvedItems = await upsertProductos(form.items);
      setForm((cur) => ({
        ...cur,
        cliente_id: String(clienteId),
        items: resolvedItems,
      }));
      const quote = await cotizacionesSvc.create(buildQuotePayload(clienteId, resolvedItems));
      await cotizacionesSvc.facturar(quote.id, {
        tipo_comprobante: form.tipo_comprobante,
        tipo_operacion: form.tipo_operacion,
        serie_override: seriesPreview,
      });
      if (form.enviar_correo) {
        const share = await cotizacionesSvc.share(quote.id);
        if (share.mailto_link) window.open(share.mailto_link, '_blank', 'noopener,noreferrer');
      }
      toast(`${tipoLabel} emitida correctamente`);
      navigate(`/cotizaciones/${quote.id}`);
    } catch (err) {
      toast(err.message || 'No se pudo emitir el comprobante', 'error');
    } finally {
      setSaving(false);
      setConfirmOpen(false);
    }
  };

  // ─── Derived for aside ───────────────────────────────────────────────────

  const hasValidationErrors = Object.keys(errors).length > 0;

  if (loadingData) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  }

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <>
      <div className="page-shell comprobante-builder-page">

        {/* Header */}
        <div className="page-header comprobante-builder-header">
          <div>
            <Link to={backTarget} className="comprobante-back-link">
              <ArrowLeft size={14} /> Volver al listado
            </Link>
            <h1 className="page-title">Nueva {tipoLabel}</h1>
            <p className="page-subtitle">Emisión electrónica · {seriesPreview}-XXXXXX</p>
          </div>
          <div className="comprobante-toolbar">
            <button className="btn-secondary" type="button" onClick={() => setPreviewOpen(true)}>
              <Eye size={14} /> Vista previa
            </button>
          </div>
        </div>

        {/* Type switcher — prominent */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
          <DocumentTypeSwitcher
            value={form.tipo_comprobante}
            onChange={(v) => setRootField('tipo_comprobante', v)}
            options={['01', '03']}
          />
          <ModeSwitch mode={form.modo_emision} onChange={(v) => setRootField('modo_emision', v)} />
        </div>

        <div className="comprobante-top-grid">

          {/* ── Document metadata ── */}
          <SectionCard kicker="Documento" title="Datos del comprobante">
            <div className="comprobante-field-grid comprobante-field-grid--document">

              <label className="comprobante-field">
                <span className="label">Moneda</span>
                <CustomSelect value={form.moneda} onChange={(v) => setRootField('moneda', v)}
                  options={[{ value: 'PEN', label: 'S/ Soles' }, { value: 'USD', label: '$ Dólares' }]} />
              </label>

              {form.tipo_comprobante === '01' && (
                <label className="comprobante-field">
                  <span className="label">Tipo de operación</span>
                  <CustomSelect value={form.tipo_operacion} onChange={(v) => setRootField('tipo_operacion', v)} options={OPERATION_OPTIONS} />
                </label>
              )}

              <label className="comprobante-field">
                <span className="label">Forma de pago</span>
                <CustomSelect value={form.condicion_pago} onChange={(v) => setRootField('condicion_pago', v)} options={PAYMENT_OPTIONS} />
              </label>

              <label className="comprobante-field">
                <span className="label">Medio de pago</span>
                <CustomSelect value={form.medio_pago} onChange={(v) => setRootField('medio_pago', v)} options={MEDIO_PAGO_OPTIONS} />
              </label>

              <label className="comprobante-field">
                <span className="label">Fecha emisión</span>
                <DatePicker value={form.fecha_emision} onChange={(v) => setRootField('fecha_emision', v)} />
              </label>

              <label className="comprobante-field">
                <span className="label">Fecha vencimiento</span>
                <DatePicker value={form.fecha_vencimiento} disabled={form.condicion_pago === 'contado'} onChange={(v) => setRootField('fecha_vencimiento', v)} />
              </label>

              <div className="comprobante-field comprobante-field-span-2">
                <span className="label">Precio incluye IGV</span>
                <div className="comprobante-switch-row">
                  <BuilderSwitch
                    label={form.incluye_igv ? 'Los precios ya incluyen IGV' : 'Los precios son sin IGV'}
                    checked={form.incluye_igv}
                    onChange={handleIgvToggle}
                  />
                  <p style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                    {form.incluye_igv ? 'El IGV se desglosa desde el precio ingresado.' : 'El IGV se agrega sobre el precio ingresado.'}
                  </p>
                </div>
              </div>

              <label className="comprobante-field comprobante-field-span-2">
                <span className="label">Observaciones</span>
                <textarea className="input resize-none" rows={2} value={form.observaciones}
                  onChange={(e) => setRootField('observaciones', e.target.value)}
                  placeholder="Condiciones especiales, instrucciones de entrega..." />
              </label>
            </div>
          </SectionCard>

          {/* ── Client ── */}
          <div className="comprobante-right-stack">
            <SectionCard kicker="Receptor" title="Datos del cliente">
              <div className="comprobante-field-grid comprobante-field-grid--client">
                <div className="comprobante-field comprobante-field-span-2">
                  <span className="label">Cliente</span>
                  <ClientCombobox
                    clients={clientes}
                    value={form.cliente_id}
                    onChange={(id) => setRootField('cliente_id', id)}
                    onFormChange={handleClientFormChange}
                  />
                  <FieldError message={errors.numero_documento} />
                  <FieldError message={errors.razon_social} />
                </div>

                <div className="comprobante-field">
                  <span className="label">Enviar correo al emitir</span>
                  <BuilderSwitch label="Correo" checked={form.enviar_correo} onChange={(v) => setRootField('enviar_correo', v)} accent="success" />
                </div>
              </div>
            </SectionCard>
          </div>
        </div>

        {/* ── Lines table ── */}
        <div className="comprobante-bottom-grid">
          <SectionCard
            kicker="Productos / Servicios"
            title="Líneas del comprobante"
            aside={(
              <div className="comprobante-lines-actions">
                <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleImportCsv} />
                <button type="button" className="btn-secondary" onClick={() => fileRef.current?.click()}>
                  <FileUp size={14} /> Subir CSV
                </button>
                <button type="button" className="btn-primary" onClick={addItem}>
                  <Plus size={14} /> Agregar línea
                </button>
              </div>
            )}
          >
            <div className="comprobante-lines-table">
              <div className="comprobante-lines-head" style={{ gridTemplateColumns: '3fr 0.8fr 0.9fr 1fr 1fr 0.65fr' }}>
                <span>Código / Producto</span>
                <span>Unidad</span>
                <span style={{ textAlign: 'right' }}>Cant.</span>
                <span style={{ textAlign: 'right' }}>P. Unitario</span>
                <span style={{ textAlign: 'right' }}>Total</span>
                <span />
              </div>

              <div className="comprobante-lines-wrap comprobante-lines-wrap--table" style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                {form.items.map((item, index) => (
                  <LineRow
                    key={item.key}
                    item={item}
                    index={index}
                    moneda={form.moneda}
                    incluyeIgv={form.incluye_igv}
                    products={productos}
                    isLast={index === form.items.length - 1}
                    onItemChange={handleItemChange}
                    onFieldChange={setItemField}
                    onRemove={removeItem}
                    onAddNext={addItem}
                  />
                ))}
              </div>
            </div>

            {errors.items && (
              <div style={{ padding: '8px 16px' }}>
                <FieldError message={errors.items} />
              </div>
            )}
          </SectionCard>

          {/* ── Summary aside ── */}
          <aside className="comprobante-builder-aside" style={{ position: 'sticky', top: '16px', alignSelf: 'flex-start' }}>
            <div className="comprobante-summary-card">
              <div className="comprobante-summary-head">
                <div>
                  <p className="comprobante-section-kicker">Resumen</p>
                  <h3 className="comprobante-section-title">Total del comprobante</h3>
                </div>
              </div>

              <div className="comprobante-summary-inline">
                <span className="comprobante-flag">{form.tipo_comprobante === '01' ? 'Factura' : 'Boleta'}</span>
                <span className="comprobante-summary-chip">{seriesPreview}</span>
                <span className="comprobante-summary-chip">{form.items.length} línea{form.items.length !== 1 ? 's' : ''}</span>
              </div>

              <div className="comprobante-summary-totals">
                <div><span>Subtotal (sin IGV)</span><strong>{formatCurrency(totals.subtotal, form.moneda)}</strong></div>
                <div><span>IGV (18%)</span><strong>{formatCurrency(totals.igv, form.moneda)}</strong></div>
                <div className="is-total"><span>Total</span><strong>{formatCurrency(totals.total, form.moneda)}</strong></div>
              </div>

              {/* Validation summary */}
              <ValidationSummary errors={errors} />

              <div className="comprobante-summary-actions">
                <button className="btn-secondary" type="button" onClick={() => setPreviewOpen(true)}>
                  <Eye size={14} /> Vista previa
                </button>
                <button
                  className="btn-primary"
                  type="button"
                  onClick={handleEmitClick}
                  disabled={saving}
                  style={{ flex: 1 }}
                >
                  {saving ? <Spinner size="sm" /> : null}
                  Emitir {form.tipo_comprobante === '01' ? 'Factura' : 'Boleta'}
                </button>
              </div>

              <div className="comprobante-summary-note">
                <p>{form.cliente.razon_social || 'Sin cliente seleccionado'}</p>
                {form.enviar_correo && (
                  <div className="comprobante-summary-email">
                    <Mail size={13} /> Correo habilitado al emitir.
                  </div>
                )}
              </div>
            </div>
          </aside>
        </div>
      </div>

      {/* Preview modal */}
      <PreviewModal open={previewOpen} onClose={() => setPreviewOpen(false)} form={form} totals={totals} tenantData={tenantData} />

      {/* Confirm emit dialog */}
      <ConfirmEmitDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleEmitConfirmed}
        loading={saving}
        mode="emit"
        tipo={form.tipo_comprobante}
        serie={`${seriesPreview}-XXXXXX`}
        cliente={form.cliente.razon_social}
        total={totals.total}
        moneda={form.moneda}
        extraLines={[
          `${form.cliente.tipo_documento === '6' ? 'RUC' : 'DNI'} ${form.cliente.numero_documento}`,
          `${form.items.length} línea${form.items.length !== 1 ? 's' : ''} · ${PAYMENT_OPTIONS.find((o) => o.value === form.condicion_pago)?.label}`,
        ]}
      />

      {/* IGV toggle confirmation */}
      <Modal open={igvConfirmOpen} onClose={() => setIgvConfirmOpen(false)} title="Cambiar modo de precios" size="sm">
        <div className="space-y-4">
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Cambiar el modo de IGV va a <strong>recalcular los precios</strong> de todas las líneas ya ingresadas ({form.items.filter((it) => Number(it.precio_unitario) > 0).length} línea{form.items.filter((it) => Number(it.precio_unitario) > 0).length !== 1 ? 's' : ''}). ¿Sí, cambiar?
          </p>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button className="btn-secondary" onClick={() => setIgvConfirmOpen(false)}>Cancelar</button>
            <button className="btn-primary" onClick={() => { applyIgvToggle(pendingIgv); setIgvConfirmOpen(false); }}>
              Sí, recalcular precios
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
