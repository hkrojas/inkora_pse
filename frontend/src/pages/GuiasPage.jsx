import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, Plus, PlusCircle, Trash2, Truck, MapPin, ChevronDown, AlertCircle, Search, Download, Package, CheckCircle2, FileX, ArrowRight, Clock3 } from 'lucide-react';
import { guias as svc } from '../services/guias';
import { cotizaciones as cotSvc } from '../services/cotizaciones';
import { clientes as cliSvc } from '../services/clientes';
import Spinner from '../components/ui/Spinner';
import { PageError } from '../components/ui/PageState';
import EmptyState from '../components/ui/EmptyState';
import Badge from '../components/ui/Badge';
import Drawer from '../components/ui/Drawer';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import Pagination from '../components/ui/Pagination';
import { FieldError } from '../components/ui/FieldError';
import { useToast } from '../components/ui/Toast';
import { getGuideStatusMeta } from '../lib/utils/fiscalStatus';
import { getPageCount } from '../lib/utils/queryParams';
import { SUNAT_UNIT_OPTIONS } from '../lib/utils/sunatCatalogs';

// ─── Constants ────────────────────────────────────────────────────────────────

const MOTIVO_OPTS = [
  { value: '01', label: '01 – Venta' },
  { value: '02', label: '02 – Compra' },
  { value: '04', label: '04 – Traslado entre establecimientos' },
  { value: '13', label: '13 – Otros' },
];

const MODALIDAD_OPTS = [
  { value: '01', label: '01 – Transporte público' },
  { value: '02', label: '02 – Transporte privado' },
];

const UNIT_OPTS = SUNAT_UNIT_OPTIONS.filter((unit) => unit.value !== 'ZZ');
const PER_PAGE = 15;
const DEFAULT_GUIDE_COUNTS = {
  all: 0,
  pending: 0,
  smartpse: 0,
  transit: 0,
  emitted: 0,
  cancelled: 0,
  voided: 0,
};

const MOTIVO_LABELS = new Map([
  ['01', 'Venta'],
  ['02', 'Compra'],
  ['04', 'Traslado entre establecimientos'],
  ['13', 'Otros'],
]);

const EMPTY_ITEM = () => ({ descripcion: '', cantidad: 1, unidad_medida: 'NIU' });

// ─── Ubigeo search (simple inline) ───────────────────────────────────────────

// Common Lima ubigeos for quick lookup — extend or replace with a full JSON
const UBIGEO_SAMPLES = [
  { code: '150101', label: 'Lima – Lima – Lima' },
  { code: '150102', label: 'Lima – Lima – Ancón' },
  { code: '150103', label: 'Lima – Lima – Ate' },
  { code: '150104', label: 'Lima – Lima – Barranco' },
  { code: '150105', label: 'Lima – Lima – Breña' },
  { code: '150106', label: 'Lima – Lima – Carabayllo' },
  { code: '150107', label: 'Lima – Lima – Chaclacayo' },
  { code: '150108', label: 'Lima – Lima – Chorrillos' },
  { code: '150110', label: 'Lima – Lima – Comas' },
  { code: '150112', label: 'Lima – Lima – El Agustino' },
  { code: '150114', label: 'Lima – Lima – Jesús María' },
  { code: '150115', label: 'Lima – Lima – La Molina' },
  { code: '150116', label: 'Lima – Lima – La Victoria' },
  { code: '150117', label: 'Lima – Lima – Lince' },
  { code: '150118', label: 'Lima – Lima – Los Olivos' },
  { code: '150119', label: 'Lima – Lima – Lurigancho' },
  { code: '150120', label: 'Lima – Lima – Lurín' },
  { code: '150121', label: 'Lima – Lima – Magdalena del Mar' },
  { code: '150122', label: 'Lima – Lima – Miraflores' },
  { code: '150127', label: 'Lima – Lima – Pueblo Libre' },
  { code: '150128', label: 'Lima – Lima – Puente Piedra' },
  { code: '150130', label: 'Lima – Lima – Rímac' },
  { code: '150131', label: 'Lima – Lima – San Borja' },
  { code: '150132', label: 'Lima – Lima – San Isidro' },
  { code: '150134', label: 'Lima – Lima – San Miguel' },
  { code: '150136', label: 'Lima – Lima – Santiago de Surco' },
  { code: '150137', label: 'Lima – Lima – Surquillo' },
  { code: '150138', label: 'Lima – Lima – Villa El Salvador' },
  { code: '150139', label: 'Lima – Lima – Villa María del Triunfo' },
  { code: '070101', label: 'Callao – Callao – Callao' },
  { code: '040101', label: 'Arequipa – Arequipa – Arequipa' },
  { code: '130101', label: 'La Libertad – Trujillo – Trujillo' },
  { code: '140101', label: 'Lambayeque – Chiclayo – Chiclayo' },
  { code: '150901', label: 'Lima – Huarochirí – Matucana' },
];

function UbigeoSelect({ value, onChange, placeholder }) {
  return (
    <CustomSelect
      value={value}
      onChange={onChange}
      searchable
      searchPlaceholder="Buscar distrito, provincia..."
      placeholder={placeholder || 'Seleccionar ubigeo...'}
      options={UBIGEO_SAMPLES.map((u) => ({ value: u.code, label: `${u.code} – ${u.label}`, searchText: `${u.code} ${u.label}` }))}
      filterOption={(opt, q) => opt.searchText?.toLowerCase().includes(q)}
      renderPreview={(opt) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700 }}>{opt.value}</span>
      )}
    />
  );
}

// ─── Guia form ────────────────────────────────────────────────────────────────

function NuevaGuiaForm({ onSave, onCancel, saving, clientes, cotizaciones }) {
  const [tab, setTab]       = useState('general');
  const [items, setItems]   = useState([EMPTY_ITEM()]);
  const [errors, setErrors] = useState({});
  const [form, setForm] = useState({
    cotizacion_id:       '',
    cliente_id:          '',
    fecha_traslado:      new Date().toISOString().slice(0, 10),
    motivo_traslado:     '01',
    descripcion_motivo:  'Venta',
    modalidad_traslado:  '01',
    partida_ubigeo:      '',
    partida_direccion:   '',
    llegada_ubigeo:      '',
    llegada_direccion:   '',
    peso_bruto_total:    '',
    unidad_medida_peso:  'KGM',
    // Transportista (público)
    ruc_transportista:   '',
    nombre_transportista:'',
    placa_vehiculo:      '',
    licencia_conductor:  '',
  });

  const set = (key) => (val) => setForm((c) => ({ ...c, [key]: typeof val === 'object' && val?.target ? val.target.value : val }));

  const setItem = (index, key, value) =>
    setItems((cur) => cur.map((it, i) => i === index ? { ...it, [key]: value } : it));

  const needsTransportista = form.modalidad_traslado === '01';

  const validate = () => {
    const e = {};
    if (form.motivo_traslado !== '04' && !form.cliente_id && !form.cotizacion_id) {
      e.cliente_id = 'Selecciona un cliente destinatario o una cotizacion de referencia';
    }
    if (!form.partida_direccion.trim()) e.partida_direccion = 'Dirección de partida es obligatoria';
    if (!form.partida_ubigeo)           e.partida_ubigeo   = 'Ubigeo de partida es obligatorio';
    if (!form.llegada_direccion.trim()) e.llegada_direccion = 'Dirección de llegada es obligatoria';
    if (!form.llegada_ubigeo)           e.llegada_ubigeo   = 'Ubigeo de llegada es obligatorio';
    if (!form.peso_bruto_total || Number(form.peso_bruto_total) <= 0) e.peso = 'Peso bruto es obligatorio';
    if (needsTransportista) {
      if (!form.ruc_transportista.trim()) e.ruc_transportista = 'RUC del transportista es obligatorio';
      if (!form.placa_vehiculo.trim())    e.placa_vehiculo    = 'Placa del vehículo es obligatoria';
    }
    if (!items.some((it) => it.descripcion.trim())) e.items = 'Agrega al menos un bien a trasladar';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) {
      // Navigate to first tab with error
      if (errors.peso || errors.partida_direccion || errors.llegada_direccion) setTab('ruta');
      return;
    }
    onSave({
      cotizacion_id: form.cotizacion_id ? Number(form.cotizacion_id) : null,
      cliente_id: form.cliente_id ? Number(form.cliente_id) : null,
      fecha_traslado: new Date(form.fecha_traslado).toISOString(),
      motivo_traslado: form.motivo_traslado,
      descripcion_motivo: form.descripcion_motivo,
      modalidad_traslado: form.modalidad_traslado,
      partida_ubigeo: form.partida_ubigeo,
      partida_direccion: form.partida_direccion.trim(),
      llegada_ubigeo: form.llegada_ubigeo,
      llegada_direccion: form.llegada_direccion.trim(),
      peso_bruto_total: Number(form.peso_bruto_total),
      unidad_medida_peso: form.unidad_medida_peso,
      transportista_ruc: form.ruc_transportista.trim() || null,
      transportista_razon_social: form.nombre_transportista.trim() || null,
      vehiculo_placa: form.placa_vehiculo.trim().toUpperCase() || null,
      conductor_licencia: form.licencia_conductor.trim().toUpperCase() || null,
      items: items.map((it) => ({
        ...it,
        descripcion: it.descripcion.trim(),
        cantidad: Number(it.cantidad),
      })),
    });
  };

  const clienteOptions = clientes.map((c) => ({
    value: String(c.id),
    label: c.razon_social || c.nombre || '',
    searchText: `${c.razon_social || c.nombre} ${c.numero_documento}`,
  }));

  const cotizacionOptions = cotizaciones.map((c) => ({
    value: String(c.id),
    label: `${c.internal_order_number || `#${c.id}`} — ${c.cliente_nombre || ''}`,
    searchText: `${c.internal_order_number || c.id} ${c.cliente_nombre || ''}`,
  }));

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'ruta',    label: 'Ruta' },
    { id: 'bienes',  label: 'Bienes' },
    ...(needsTransportista ? [{ id: 'transportista', label: 'Transportista' }] : []),
  ];

  return (
    <form onSubmit={handleSubmit} className="guide-form">

      {/* Tabs */}
      <div className="guide-form-tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`guide-form-tab${tab === t.id ? ' is-active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab: General ── */}
      {tab === 'general' && (
        <div className="guide-form-grid guide-form-panel">
          <div>
            <label className="label">Motivo de traslado</label>
            <CustomSelect value={form.motivo_traslado} onChange={set('motivo_traslado')} options={MOTIVO_OPTS} />
          </div>
          <div>
            <label className="label">Modalidad</label>
            <CustomSelect value={form.modalidad_traslado} onChange={set('modalidad_traslado')} options={MODALIDAD_OPTS} />
          </div>
          <div>
            <label className="label">Fecha de traslado</label>
            <DatePicker value={form.fecha_traslado} onChange={set('fecha_traslado')} required />
          </div>
          <div>
            <label className="label">Peso bruto total (KGM)</label>
            <div className="guide-form-number-wrap">
              <input
                required
                type="number"
                step="0.001"
                min="0.001"
                className="input guide-form-number-input"
                value={form.peso_bruto_total}
                onChange={set('peso_bruto_total')}
                placeholder="0.000"
              />
              <span className="guide-form-number-unit">KGM</span>
            </div>
            <FieldError message={errors.peso} />
          </div>
          <div className="guide-form-field--full">
            <label className="label">Cliente destinatario</label>
            <CustomSelect
              value={form.cliente_id}
              onChange={set('cliente_id')}
              options={clienteOptions}
              searchable
              searchPlaceholder="Buscar cliente..."
              placeholder="Seleccionar cliente destinatario"
              filterOption={(opt, q) => opt.searchText?.toLowerCase().includes(q)}
            />
            <FieldError message={errors.cliente_id} />
          </div>
          <div className="guide-form-field--full">
            <label className="label">Cotización de referencia</label>
            <CustomSelect
              value={String(form.cotizacion_id)}
              onChange={set('cotizacion_id')}
              options={cotizacionOptions}
              searchable
              searchPlaceholder="Buscar cotización..."
              placeholder="Opcional si ya seleccionaste cliente"
              filterOption={(opt, q) => opt.searchText?.toLowerCase().includes(q)}
            />
          </div>
        </div>
      )}

      {/* ── Tab: Ruta ── */}
      {tab === 'ruta' && (
        <div className="guide-form-grid guide-form-panel">
          {/* Partida */}
          <div className="guide-form-section">
            <div className="guide-form-section-title">
              <MapPin size={13} />
              <p>Punto de partida</p>
            </div>
            <div>
              <label className="label">Dirección</label>
              <input required className="input" value={form.partida_direccion} onChange={set('partida_direccion')} placeholder="Av. Los Pinos 123, Lima" />
              <FieldError message={errors.partida_direccion} />
            </div>
            <div>
              <label className="label">Ubigeo</label>
              <UbigeoSelect value={form.partida_ubigeo} onChange={set('partida_ubigeo')} placeholder="Seleccionar ubigeo de partida..." />
              <FieldError message={errors.partida_ubigeo} />
            </div>
          </div>

          {/* Llegada */}
          <div className="guide-form-section">
            <div className="guide-form-section-title guide-form-section-title--accent">
              <MapPin size={13} />
              <p>Punto de llegada</p>
            </div>
            <div>
              <label className="label">Dirección</label>
              <input required className="input" value={form.llegada_direccion} onChange={set('llegada_direccion')} placeholder="Jr. El Sol 456, Ate" />
              <FieldError message={errors.llegada_direccion} />
            </div>
            <div>
              <label className="label">Ubigeo</label>
              <UbigeoSelect value={form.llegada_ubigeo} onChange={set('llegada_ubigeo')} placeholder="Seleccionar ubigeo de llegada..." />
              <FieldError message={errors.llegada_ubigeo} />
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Bienes ── */}
      {tab === 'bienes' && (
        <div className="guide-form-body guide-form-panel">
          <FieldError message={errors.items} />
          <div className="guide-items-table">
            <div className="ink-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Descripción del bien</th>
                    <th>Unidad</th>
                    <th>Cant.</th>
                    <th aria-label="Acciones" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <tr key={index}>
                      <td className="spreadsheet-cell">
                        <input required className="spreadsheet-input" placeholder="Descripción..." value={item.descripcion} onChange={(e) => setItem(index, 'descripcion', e.target.value)} />
                      </td>
                      <td className="spreadsheet-cell">
                        <CustomSelect compact value={item.unidad_medida} onChange={(v) => setItem(index, 'unidad_medida', v)} options={UNIT_OPTS} />
                      </td>
                      <td className="spreadsheet-cell">
                        <input required type="number" min="1" className="spreadsheet-input spreadsheet-input-mono" value={item.cantidad} onChange={(e) => setItem(index, 'cantidad', e.target.value)} />
                      </td>
                      <td className="guide-items-table-action">
                        {items.length > 1 && (
                          <button type="button" className="guide-item-remove" onClick={() => setItems((cur) => cur.filter((_, i) => i !== index))}>
                            <Trash2 style={{ width: '14px', height: '14px' }} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="guide-items-table-add">
              <button type="button" onClick={() => setItems((cur) => [...cur, EMPTY_ITEM()])}>
                <PlusCircle style={{ width: '14px', height: '14px' }} /> Agregar bien
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Transportista ── */}
      {tab === 'transportista' && (
        <div className="guide-form-grid guide-form-panel">
          <div className="guide-form-alert guide-form-field--full">
            <AlertCircle size={14} />
            Modalidad pública requiere datos del transportista para SUNAT.
          </div>
          <div>
            <label className="label">RUC del transportista <span className="guide-form-required">*</span></label>
            <input className="input guide-form-code-input" value={form.ruc_transportista} onChange={set('ruc_transportista')} placeholder="20XXXXXXXXX" maxLength={11} />
            <FieldError message={errors.ruc_transportista} />
          </div>
          <div>
            <label className="label">Razón social del transportista</label>
            <input className="input" value={form.nombre_transportista} onChange={set('nombre_transportista')} placeholder="Empresa de Transportes S.A.C." />
          </div>
          <div>
            <label className="label">Placa del vehículo <span className="guide-form-required">*</span></label>
            <input className="input guide-form-code-input guide-form-code-input--upper" value={form.placa_vehiculo} onChange={set('placa_vehiculo')} placeholder="ABC-123" />
            <FieldError message={errors.placa_vehiculo} />
          </div>
          <div>
            <label className="label">Licencia del conductor</label>
            <input className="input guide-form-code-input guide-form-code-input--normal" value={form.licencia_conductor} onChange={set('licencia_conductor')} placeholder="Q12345678" />
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="modal-footer guide-form-footer">
        <button type="button" onClick={onCancel} className="btn-secondary guide-form-cancel">Cancelar</button>
        <div className="guide-form-actions">
          {tab !== tabs[tabs.length - 1].id && (
            <button type="button" onClick={() => setTab(tabs[tabs.findIndex((t) => t.id === tab) + 1].id)} className="btn-secondary guide-form-next">
              Siguiente <ChevronDown size={13} className="guide-form-next-icon" />
            </button>
          )}
          <button type="submit" disabled={saving} className="btn-primary guide-form-submit">
            {saving ? <Spinner size="sm" /> : <Truck size={14} />} Guardar borrador
          </button>
        </div>
      </div>
    </form>
  );
}

export default function GuiasPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [clientes, setClientes] = useState([]);
  const [cotizaciones, setCotizaciones] = useState([]);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [counts, setCounts] = useState(DEFAULT_GUIDE_COUNTS);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    motivo: 'all',
    modalidad: 'all',
    desde: '',
    hasta: '',
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setPage(1);
      setDebouncedSearch(search.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    svc.list({
      skip: (page - 1) * PER_PAGE,
      limit: PER_PAGE,
      q: debouncedSearch || undefined,
      tab: activeTab,
      motivo: filters.motivo === 'all' ? undefined : filters.motivo,
      modalidad: filters.modalidad === 'all' ? undefined : filters.modalidad,
      desde: filters.desde || undefined,
      hasta: filters.hasta || undefined,
    })
      .then((data) => {
        setList(Array.isArray(data.items) ? data.items : []);
        setTotal(Number(data.total || 0));
        setCounts({ ...DEFAULT_GUIDE_COUNTS, ...(data.counts || {}) });
      })
      .catch((err) => {
        setError(err);
        setList([]);
        setTotal(0);
        setCounts(DEFAULT_GUIDE_COUNTS);
        toast(err.message || 'No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error');
      })
      .finally(() => setLoading(false));
  }, [activeTab, debouncedSearch, filters, page, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    Promise.all([cliSvc.page('?limit=15'), cotSvc.list()])
      .then(([c, cot]) => {
        setClientes(Array.isArray(c) ? c : c?.items || []);
        setCotizaciones(Array.isArray(cot) ? cot : []);
      })
      .catch(() => {});
  }, []);

  const handleSave = async (data) => {
    setSaving(true);
    try {
      const created = await svc.create(data);
      toast('Borrador guardado. Revisa la guía antes de enviarla a SUNAT.', 'success');
      setModal(false);
      navigate(`/guias/${created.id}`);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleTabChange = (key) => {
    setActiveTab(key);
    setPage(1);
  };

  const setFilter = (key, value) => {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const clearFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setPage(1);
    setFilters({ motivo: 'all', modalidad: 'all', desde: '', hasta: '' });
  };

  const quoteLookup = useMemo(() => {
    const byId = new Map();
    const byOrder = new Map();

    cotizaciones.forEach((quote) => {
      const normalizedId = Number(quote.id);
      if (!Number.isNaN(normalizedId)) byId.set(normalizedId, quote);
      if (quote.internal_order_number) byOrder.set(quote.internal_order_number, quote);
    });

    return { byId, byOrder };
  }, [cotizaciones]);

  const clientLookup = useMemo(() => {
    const map = new Map();
    clientes.forEach((client) => {
      const normalizedId = Number(client.id);
      if (!Number.isNaN(normalizedId)) map.set(normalizedId, client);
    });
    return map;
  }, [clientes]);

  const resolveRelatedQuote = (item) => {
    if (item?.source_quote_id && quoteLookup.byId.has(Number(item.source_quote_id))) {
      return quoteLookup.byId.get(Number(item.source_quote_id));
    }
    if (item?.cotizacion_id && quoteLookup.byId.has(Number(item.cotizacion_id))) {
      return quoteLookup.byId.get(Number(item.cotizacion_id));
    }
    if (item?.internal_order_number && quoteLookup.byOrder.has(item.internal_order_number)) {
      return quoteLookup.byOrder.get(item.internal_order_number);
    }
    return null;
  };

  const getRecipientData = (item) => {
    const relatedQuote = resolveRelatedQuote(item);
    const quoteClient = relatedQuote?.cliente;
    const fallbackClient = relatedQuote?.cliente_id
      ? clientLookup.get(Number(relatedQuote.cliente_id))
      : null;

    const name =
      item?.cliente_nombre ||
      item?.destinatario_nombre ||
      quoteClient?.razon_social ||
      quoteClient?.nombre ||
      relatedQuote?.cliente_nombre ||
      fallbackClient?.razon_social ||
      fallbackClient?.nombre ||
      'Sin cliente vinculado';

    const document =
      item?.cliente_documento ||
      item?.destinatario_documento ||
      quoteClient?.numero_documento ||
      relatedQuote?.cliente_documento ||
      fallbackClient?.numero_documento ||
      '';

    return { name, document };
  };

  const getReferenceData = (item) => {
    const relatedQuote = resolveRelatedQuote(item);
    const primary =
      item?.internal_order_number ||
      relatedQuote?.internal_order_number ||
      (item?.cotizacion_id ? `COT-${item.cotizacion_id}` : 'Sin referencia');

    const secondary =
      item?.cotizacion_id
        ? `Cotizacion #${item.cotizacion_id}`
        : relatedQuote?.id
          ? `Cotizacion #${relatedQuote.id}`
          : 'Sin cotizacion vinculada';

    return { primary, secondary };
  };

  const pageItems = list;
  const guidePageCount = getPageCount(total, PER_PAGE);

  useEffect(() => {
    if (page > guidePageCount) setPage(guidePageCount);
  }, [guidePageCount, page]);

  const hasActiveFilters = Boolean(
    search || filters.motivo !== 'all' || filters.modalidad !== 'all' || filters.desde || filters.hasta,
  );
  const pristineEmpty = !loading && !error && counts.all === 0 && !hasActiveFilters && activeTab === 'all';

  const heroCards = [
    {
      key: 'pending',
      value: counts.pending,
      label: 'Pendientes',
      text: counts.smartpse ? `${counts.smartpse} en espera Smart PSE` : counts.all ? `${Math.round((counts.pending / counts.all) * 100)}% del flujo actual` : 'Sin salidas pendientes',
      link: 'Ver pendientes',
      icon: <Package size={16} />,
    },
    {
      key: 'transit',
      value: counts.transit,
      label: 'En tránsito',
      text: counts.transit ? 'Despachos en movimiento' : 'Sin rutas activas',
      link: 'Revisar ruta',
      icon: <Truck size={16} />,
    },
    {
      key: 'emitted',
      value: counts.emitted,
      label: 'Emitidas',
      text: counts.emitted ? 'Listas para seguimiento' : 'Aún sin emitidas',
      link: 'Abrir emitidas',
      icon: <CheckCircle2 size={16} />,
    },
    {
      key: 'voided',
      value: counts.voided,
      label: 'Anuladas',
      text: counts.voided ? 'Histórico con estado final' : 'Sin anulaciones registradas',
      link: 'Ver histórico',
      icon: <FileX size={16} />,
    },
  ];

  const motivoFilterOptions = useMemo(
    () => [{ value: 'all', label: 'Todos' }, ...MOTIVO_OPTS],
    [],
  );

  const modalidadFilterOptions = useMemo(
    () => [{ value: 'all', label: 'Todas' }, ...MODALIDAD_OPTS],
    [],
  );

  return (
    <div className="page-shell page-shell--dense guias-page">
      <div className="page-head ink-enter-1">
        <div className="page-actions document-list-page-actions">
          <button
            type="button"
            className="btn"
            onClick={() => toast('La exportación de guías estará disponible pronto.', 'info')}
          >
            <Download className="h-4 w-4" />
            Exportar
          </button>
          <button className="btn-primary flex items-center gap-2" onClick={() => setModal(true)}>
            <Plus className="h-4 w-4" />
            Nueva guía
          </button>
        </div>
      </div>

      <section className="attention document-list-hero ink-enter-2">
        <div className="attention-title document-list-hero-title">
          <div className="document-list-hero-head">
            <div className="attention-title-badge">
              <Truck size={15} />
            </div>
          </div>

          <div className="document-list-hero-pagecopy">
            <h2>Guías de remisión</h2>
            <p>Despacho fiscal y seguimiento operativo desde una sola bandeja.</p>
          </div>

          <div className="document-list-hero-kicker">
            Despacho fiscal · {counts.pending ? `${counts.pending} por salir` : 'Operación estable'}
          </div>
        </div>

        {!pristineEmpty && heroCards.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`attention-card document-list-hero-card${activeTab === item.key ? ' is-active' : ''}`}
            onClick={() => handleTabChange(item.key)}
          >
            <div className="document-list-hero-card-icon">{item.icon}</div>
            <strong>{item.value}</strong>
            <div className="attention-card-text">
              {item.label}
              <span>{item.text}</span>
            </div>
            <span className="attention-card-link">
              {item.link}
              <ArrowRight size={13} />
            </span>
          </button>
        ))}
      </section>

      <article className="panel document-list-panel ink-enter-3">
        {!pristineEmpty && <>
        <div className="toolbar">
          <label className="search-box">
            <Search size={16} />
            <input
              placeholder="Buscar por numero, referencia, origen o destino..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>

          <div className="toolbar-actions">
            {hasActiveFilters && (
              <button type="button" className="btn-ghost" onClick={clearFilters}>
                Limpiar filtros
              </button>
            )}
          </div>
        </div>

        <div className="document-list-filters">
          <div className="document-list-filter">
            <span>Motivo</span>
            <CustomSelect compact value={filters.motivo} onChange={(value) => setFilter('motivo', value)} options={motivoFilterOptions} />
          </div>
          <div className="document-list-filter">
            <span>Modalidad</span>
            <CustomSelect compact value={filters.modalidad} onChange={(value) => setFilter('modalidad', value)} options={modalidadFilterOptions} />
          </div>
          <div className="document-list-filter">
            <span>Desde</span>
            <DatePicker compact value={filters.desde} onChange={(value) => setFilter('desde', value)} />
          </div>
          <div className="document-list-filter">
            <span>Hasta</span>
            <DatePicker compact value={filters.hasta} onChange={(value) => setFilter('hasta', value)} />
          </div>
        </div>

        <div className="segments-row">
          <div className="segments">
            {[
              { key: 'all', label: 'Todas', count: counts.all },
              { key: 'pending', label: 'Pendientes', count: counts.pending },
              { key: 'smartpse', label: 'Smart PSE', count: counts.smartpse },
              { key: 'transit', label: 'En tránsito', count: counts.transit },
              { key: 'emitted', label: 'Emitidas', count: counts.emitted },
              { key: 'voided', label: 'Anuladas', count: counts.voided },
            ].map((item) => (
              <button
                key={item.key}
                type="button"
                className={`segment ${activeTab === item.key ? 'active' : ''}`}
                onClick={() => handleTabChange(item.key)}
              >
                {item.label}
                <span className="document-list-segment-count">{item.count}</span>
              </button>
            ))}
          </div>
          <div className="sort-text">
            Mostrando <strong>{pageItems.length}</strong> de <strong>{total}</strong> guías
          </div>
        </div>
        </>}

        {error ? (
          <div className="document-list-empty">
            <PageError error={error} onRetry={load} />
          </div>
        ) : loading ? (
          <div className="document-list-loading">
            <Spinner size="lg" />
          </div>
        ) : pageItems.length === 0 ? (
          <div className="document-list-empty">
            <EmptyState
              variant={pristineEmpty ? 'onboarding' : 'default'}
              icon={<Truck size={22} />}
              title={hasActiveFilters ? 'Sin resultados para estos filtros' : 'Aún no tienes guías en esta vista'}
              description={
                hasActiveFilters
                  ? 'Ajusta motivo, modalidad o fechas para recuperar despachos en esta bandeja.'
                  : 'Crea tu primera guía de remisión y sigue el despacho desde origen hasta entrega.'
              }
              action={
                hasActiveFilters ? (
                  <button className="btn-secondary" onClick={clearFilters}>Limpiar filtros</button>
                ) : (
                  <button className="btn-primary" onClick={() => setModal(true)}>Nueva guía</button>
                )
              }
            />
          </div>
        ) : (
          <div className="ink-table-card document-list-table guide-table-list">
            <div className="ink-table-header">
              <div className="ink-table-title">
                <strong>Guías operativas</strong>
                <span>{pageItems.length} visibles · {counts.pending} pendientes de salida en esta vista</span>
              </div>

              <div className="document-list-table-meta">
                <span className="document-list-table-pill">
                  <Package size={13} />
                  {counts.pending} pendientes
                </span>
                <span className="document-list-table-pill">
                  <Clock3 size={13} />
                  {counts.smartpse} Smart PSE
                </span>
                <span className="document-list-table-pill">
                  <Clock3 size={13} />
                  {counts.transit} en tránsito
                </span>
                <span className="document-list-table-pill">
                  <CheckCircle2 size={13} />
                  {counts.emitted} emitidas
                </span>
              </div>
            </div>

            <div className="ink-table-scroll">
              <table className="ink-table guide-document-table">
                <thead>
                  <tr>
                    <th>Número</th>
                    <th>Fecha traslado</th>
                    <th>Destinatario</th>
                    <th>Comprobante relacionado</th>
                    <th>Origen</th>
                    <th>Destino</th>
                    <th>Estado</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((item) => {
                    const recipient = getRecipientData(item);
                    const reference = getReferenceData(item);
                    const statusMeta = getGuideStatusMeta(item);

                    return (
                      <tr
                        key={item.id}
                        className={
                          statusMeta.tabKey === 'emitted'
                            ? 'ink-table-row--accepted'
                            : statusMeta.tabKey === 'transit'
                              ? 'ink-table-row--active'
                              : ''
                        }
                      >
                        <td data-label="Número">
                          <div className="ink-table-cell__primary document-list-folio">
                            {item.serie}-{String(item.correlativo).padStart(6, '0')}
                          </div>
                          <div className="ink-table-cell__meta">{MOTIVO_LABELS.get(String(item.motivo_traslado || '13')) || 'Otros'}</div>
                        </td>
                        <td data-label="Fecha traslado">
                          <div className="ink-table-cell__primary">
                            {item.fecha_traslado ? new Date(item.fecha_traslado).toLocaleDateString('es-PE') : '--'}
                          </div>
                          <div className="ink-table-cell__meta">
                            {item.fecha_emision ? `Emitida ${new Date(item.fecha_emision).toLocaleDateString('es-PE')}` : 'Sin fecha de emisión'}
                          </div>
                        </td>
                        <td data-label="Destinatario">
                          <div className="ink-table-cell__primary">{recipient.name}</div>
                          {recipient.document && (
                            <div className="ink-table-cell__meta">{recipient.document}</div>
                          )}
                        </td>
                        <td data-label="Comprobante relacionado">
                          <div className="ink-table-cell__primary">{reference.primary}</div>
                          <div className="ink-table-cell__meta">{reference.secondary}</div>
                        </td>
                        <td data-label="Origen">
                          <div className="ink-table-cell__primary">{item.partida_direccion || '--'}</div>
                          <div className="ink-table-cell__meta">{item.partida_ubigeo || 'Sin ubigeo'}</div>
                        </td>
                        <td data-label="Destino">
                          <div className="ink-table-cell__primary">{item.llegada_direccion || '--'}</div>
                          <div className="ink-table-cell__meta">{item.llegada_ubigeo || 'Sin ubigeo'}</div>
                        </td>
                      <td data-label="Estado" className="guide-table-status-cell">
                          <div className="flex flex-col items-start gap-1">
                            <Badge variant={statusMeta.badgeVariant}>
                              {statusMeta.label}
                            </Badge>
                            {statusMeta.helper && (
                              <span className="text-[10px] text-[var(--text-tertiary)]">
                                {statusMeta.helper}
                                {item.sunat_ticket ? ` ${item.sunat_ticket}` : ''}
                              </span>
                            )}
                          </div>
                        </td>
                      <td data-label="Acción" className="guide-table-action-cell">
                          <div className="ink-table-row-actions document-list-row-actions">
                            <Link to={`/guias/${item.id}`} className="ink-row-action-pill" title="Ver detalle">
                              <Eye className="h-3.5 w-3.5" />
                              Ver
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="ink-table-footer">
              <span className="ink-table-count">{pageItems.length} guías visibles</span>
              <Pagination page={page} totalPages={guidePageCount} onPageChange={setPage} ariaLabel="Paginación de guías" />
              <span className="ink-table-count">{counts.pending} por salir · {counts.transit} en ruta</span>
            </div>
          </div>
        )}
      </article>

      <Drawer
        open={modal}
        onClose={() => setModal(false)}
        variant="workflow"
        eyebrow="Despacho fiscal"
        status="Borrador GRE"
        initialFocus="select, input, textarea"
        title="Nueva guía de remisión"
        subtitle="Emisión GRE Smart PSE"
        icon={<Truck size={18} />}
      >
        <NuevaGuiaForm
          onSave={handleSave}
          onCancel={() => setModal(false)}
          saving={saving}
          clientes={clientes}
          cotizaciones={cotizaciones}
        />
      </Drawer>
    </div>
  );
}
