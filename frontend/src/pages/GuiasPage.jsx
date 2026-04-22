import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, Plus, PlusCircle, Trash2, Truck, MapPin, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import { guias as svc } from '../services/guias';
import { cotizaciones as cotSvc } from '../services/cotizaciones';
import { clientes as cliSvc } from '../services/clientes';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Badge, { statusBadge } from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import { FieldError } from '../components/ui/FieldError';
import ConfirmEmitDialog from '../components/documents/ConfirmEmitDialog';
import { useToast } from '../components/ui/Toast';

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

const UNIT_OPTS = [
  { value: 'NIU', label: 'NIU – Unidad' },
  { value: 'KGM', label: 'KGM – Kilogramo' },
  { value: 'ZZ',  label: 'ZZ – Servicio' },
  { value: 'MIL', label: 'MIL – Millar' },
];

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
      ...form,
      cotizacion_id:    form.cotizacion_id ? Number(form.cotizacion_id) : null,
      peso_bruto_total: Number(form.peso_bruto_total),
      fecha_traslado:   new Date(form.fecha_traslado).toISOString(),
      items:            items.map((it) => ({ ...it, cantidad: Number(it.cantidad) })),
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

  const tabStyle = (id) => ({
    padding: '8px 20px',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    border: 'none',
    borderBottom: tab === id ? '2px solid #4F46E5' : '2px solid transparent',
    background: 'none',
    color: tab === id ? '#4F46E5' : '#64748B',
    cursor: 'pointer',
  });

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 0, minHeight: '400px' }}>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #E2E8F0', padding: '0 0 0 4px', marginBottom: '0' }}>
        {tabs.map((t) => (
          <button key={t.id} type="button" style={tabStyle(t.id)} onClick={() => setTab(t.id)}>{t.label}</button>
        ))}
      </div>

      {/* ── Tab: General ── */}
      {tab === 'general' && (
        <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
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
            <div style={{ position: 'relative' }}>
              <input
                required
                type="number"
                step="0.001"
                min="0.001"
                className="input"
                style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700, paddingRight: '48px' }}
                value={form.peso_bruto_total}
                onChange={set('peso_bruto_total')}
                placeholder="0.000"
              />
              <span style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, color: '#94A3B8', pointerEvents: 'none' }}>KGM</span>
            </div>
            <FieldError message={errors.peso} />
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <label className="label">Cliente destinatario</label>
            <CustomSelect
              value={form.cliente_id}
              onChange={set('cliente_id')}
              options={clienteOptions}
              searchable
              searchPlaceholder="Buscar cliente..."
              placeholder="Sin cliente específico (opcional)"
              filterOption={(opt, q) => opt.searchText?.toLowerCase().includes(q)}
            />
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <label className="label">Cotización de referencia (opcional)</label>
            <CustomSelect
              value={String(form.cotizacion_id)}
              onChange={set('cotizacion_id')}
              options={cotizacionOptions}
              searchable
              searchPlaceholder="Buscar cotización..."
              placeholder="Sin cotización vinculada"
              filterOption={(opt, q) => opt.searchText?.toLowerCase().includes(q)}
            />
          </div>
        </div>
      )}

      {/* ── Tab: Ruta ── */}
      {tab === 'ruta' && (
        <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Partida */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MapPin size={13} style={{ color: '#475569' }} />
              <p style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#475569' }}>Punto de partida</p>
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MapPin size={13} style={{ color: '#4F46E5' }} />
              <p style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#4F46E5' }}>Punto de llegada</p>
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
        <div style={{ padding: '20px' }}>
          <FieldError message={errors.items} />
          <div style={{ background: '#fff', border: '1px solid #CBD5E1', overflow: 'hidden', marginTop: '8px' }}>
            <div className="ink-table-scroll">
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead style={{ background: '#F1F5F9', borderBottom: '1px solid #CBD5E1' }}>
                  <tr>
                    <th style={{ padding: '8px 16px', textAlign: 'left', fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', borderRight: '1px solid #E2E8F0', width: '55%' }}>Descripción del bien</th>
                    <th style={{ padding: '8px 16px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', borderRight: '1px solid #E2E8F0', width: '22%' }}>Unidad</th>
                    <th style={{ padding: '8px 16px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', borderRight: '1px solid #E2E8F0', width: '18%' }}>Cant.</th>
                    <th style={{ width: '5%', background: '#F1F5F9' }} />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <tr key={index} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td className="spreadsheet-cell" style={{ borderRight: '1px solid #E2E8F0', padding: 0 }}>
                        <input required className="spreadsheet-input" placeholder="Descripción..." value={item.descripcion} onChange={(e) => setItem(index, 'descripcion', e.target.value)} />
                      </td>
                      <td className="spreadsheet-cell" style={{ borderRight: '1px solid #E2E8F0', padding: 0 }}>
                        <CustomSelect compact value={item.unidad_medida} onChange={(v) => setItem(index, 'unidad_medida', v)} options={UNIT_OPTS} />
                      </td>
                      <td className="spreadsheet-cell" style={{ borderRight: '1px solid #E2E8F0', padding: 0 }}>
                        <input required type="number" min="1" className="spreadsheet-input spreadsheet-input-mono" value={item.cantidad} onChange={(e) => setItem(index, 'cantidad', e.target.value)} />
                      </td>
                      <td style={{ padding: 0, textAlign: 'center' }}>
                        {items.length > 1 && (
                          <button type="button" onClick={() => setItems((cur) => cur.filter((_, i) => i !== index))}
                            style={{ width: '100%', minHeight: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'none', border: 'none', color: '#CBD5E1', cursor: 'pointer' }}
                            onMouseEnter={(e) => { e.currentTarget.style.color = '#EF4444'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.color = '#CBD5E1'; }}>
                            <Trash2 style={{ width: '14px', height: '14px' }} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ padding: '8px', background: '#fff', borderTop: '1px solid #E2E8F0' }}>
              <button type="button" onClick={() => setItems((cur) => [...cur, EMPTY_ITEM()])}
                style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#4F46E5', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 16px' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = '#EEF2FF'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}>
                <PlusCircle style={{ width: '14px', height: '14px' }} /> Agregar bien
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Transportista ── */}
      {tab === 'transportista' && (
        <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', background: '#EEF2FF', border: '1px solid #C7D2FE', fontSize: '12px', color: '#4F46E5' }}>
            <AlertCircle size={14} />
            Modalidad pública requiere datos del transportista para SUNAT.
          </div>
          <div>
            <label className="label">RUC del transportista <span style={{ color: '#DC2626' }}>*</span></label>
            <input className="input" value={form.ruc_transportista} onChange={set('ruc_transportista')} placeholder="20XXXXXXXXX" maxLength={11} style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: '0.08em' }} />
            <FieldError message={errors.ruc_transportista} />
          </div>
          <div>
            <label className="label">Razón social del transportista</label>
            <input className="input" value={form.nombre_transportista} onChange={set('nombre_transportista')} placeholder="Empresa de Transportes S.A.C." />
          </div>
          <div>
            <label className="label">Placa del vehículo <span style={{ color: '#DC2626' }}>*</span></label>
            <input className="input" value={form.placa_vehiculo} onChange={set('placa_vehiculo')} placeholder="ABC-123" style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, textTransform: 'uppercase' }} />
            <FieldError message={errors.placa_vehiculo} />
          </div>
          <div>
            <label className="label">Licencia del conductor</label>
            <input className="input" value={form.licencia_conductor} onChange={set('licencia_conductor')} placeholder="Q12345678" style={{ fontFamily: 'var(--font-mono)' }} />
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="modal-footer" style={{ marginTop: 'auto' }}>
        <button type="button" onClick={onCancel} className="btn-secondary">Cancelar</button>
        <div style={{ display: 'flex', gap: '8px' }}>
          {tab !== tabs[tabs.length - 1].id && (
            <button type="button" onClick={() => setTab(tabs[tabs.findIndex((t) => t.id === tab) + 1].id)} className="btn-secondary">
              Siguiente <ChevronDown size={13} style={{ transform: 'rotate(-90deg)' }} />
            </button>
          )}
          <button type="submit" disabled={saving} className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {saving ? <Spinner size="sm" /> : <Truck size={14} />} Emitir Guía
          </button>
        </div>
      </div>
    </form>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function GuiasPage() {
  const toast = useToast();
  const [list, setList]         = useState([]);
  const [loading, setLoading]   = useState(true);
  const [modal, setModal]       = useState(false);
  const [saving, setSaving]     = useState(false);
  const [clientes, setClientes] = useState([]);
  const [cotizaciones, setCotizaciones] = useState([]);

  const load = () => {
    setLoading(true);
    svc.list()
      .then(setList)
      .catch(() => toast('Error al cargar guías', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    Promise.all([cliSvc.list(), cotSvc.list()])
      .then(([c, cot]) => { setClientes(Array.isArray(c) ? c : []); setCotizaciones(Array.isArray(cot) ? cot : []); })
      .catch(() => {});
  }, []);

  const handleSave = async (data) => {
    setSaving(true);
    try {
      await svc.create(data);
      toast('Guía emitida correctamente');
      setModal(false);
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <div className="page-header-copy">
          <p className="page-kicker">Despacho fiscal</p>
          <h2 className="page-title">Guías de remisión</h2>
          <p className="page-subtitle">{list.length} guía{list.length !== 1 ? 's' : ''} registrada{list.length !== 1 ? 's' : ''}.</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setModal(true)}>
          <Plus className="h-4 w-4" /> Nueva guía
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : list.length === 0 ? (
        <EmptyState title="Sin guías" description="Crea tu primera guía de remisión."
          action={<button className="btn-primary" onClick={() => setModal(true)}>Nueva guía</button>} />
      ) : (
        <div className="ink-table-card">
          <table className="ink-table">
            <thead>
              <tr>
                <th>Número</th>
                <th>Fecha traslado</th>
                <th>Origen</th>
                <th>Destino</th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.map((item) => (
                <tr key={item.id}>
                  <td className="font-mono-label text-xs">{item.serie}-{String(item.correlativo).padStart(6, '0')}</td>
                  <td className="text-[var(--text-secondary)]">
                    {item.fecha_traslado ? new Date(item.fecha_traslado).toLocaleDateString('es-PE') : '--'}
                  </td>
                  <td className="max-w-[160px] truncate text-[var(--text-secondary)]">{item.partida_direccion}</td>
                  <td className="max-w-[160px] truncate text-[var(--text-secondary)]">{item.llegada_direccion}</td>
                  <td><Badge variant={statusBadge(item.estado)}>{item.estado || 'pendiente'}</Badge></td>
                  <td>
                    <div className="flex justify-end">
                      <Link to={`/guias/${item.id}`} className="ink-row-btn" title="Ver detalle">
                        <Eye className="h-4 w-4" />
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modal} onClose={() => setModal(false)} title="Nueva guía de remisión" size="xl">
        <NuevaGuiaForm
          onSave={handleSave}
          onCancel={() => setModal(false)}
          saving={saving}
          clientes={clientes}
          cotizaciones={cotizaciones}
        />
      </Modal>
    </div>
  );
}
