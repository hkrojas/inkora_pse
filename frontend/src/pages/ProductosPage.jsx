import { useEffect, useState } from 'react';
import { Pencil, Plus, Search, Trash2, Save, RefreshCw } from 'lucide-react';
import { productos as svc } from '../services/productos';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Modal from '../components/ui/Modal';
import CustomSelect from '../components/ui/CustomSelect';
import { useToast } from '../components/ui/Toast';

const DOT_COLORS = ['#6366F1', '#10B981', '#F59E0B', '#3B82F6', '#8B5CF6'];

const UM_COLORS = {
  NIU: { bg: '#F0FDF4', color: '#15803D', border: '#BBF7D0' },
  ZZ:  { bg: '#EFF6FF', color: '#1D4ED8', border: '#BFDBFE' },
  KGM: { bg: '#FFF7ED', color: '#C2410C', border: '#FED7AA' },
  MTR: { bg: '#F5F3FF', color: '#7C3AED', border: '#DDD6FE' },
};
const UM_DEFAULT = { bg: '#F8FAFC', color: '#475569', border: '#E2E8F0' };
const IGV_FACTOR = 1.18;

const formatCurrency = (value) =>
  Number(value || 0).toLocaleString('es-PE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const EMPTY_FORM = {
  nombre: '',
  descripcion: '',
  precio_unitario: '',
  precio_incluye_igv: true,
  unidad_medida: 'NIU',
  codigo_interno: '',
};

function ProductoForm({ initial = EMPTY_FORM, onSave, onCancel, saving }) {
  const [form, setForm] = useState({ ...EMPTY_FORM, ...initial, precio_incluye_igv: initial?.precio_incluye_igv ?? true });

  useEffect(() => {
    setForm({ ...EMPTY_FORM, ...initial, precio_incluye_igv: initial?.precio_incluye_igv ?? true });
  }, [initial]);

  const set = (key) => (event) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));
  const precioIngresado = Number(form.precio_unitario || 0);
  const precioBase = form.precio_incluye_igv ? (precioIngresado / IGV_FACTOR) : precioIngresado;
  const precioFinal = form.precio_incluye_igv ? precioIngresado : (precioIngresado * IGV_FACTOR);
  const showPreview = Number.isFinite(precioIngresado) && precioIngresado > 0;

  return (
    <form onSubmit={(event) => { event.preventDefault(); onSave(form); }} className="space-y-4">
      <div>
        <label className="label">Nombre</label>
        <input required className="input" value={form.nombre} onChange={set('nombre')} />
      </div>

      <div>
        <label className="label">Descripcion</label>
        <textarea
          className="input min-h-[88px] resize-none"
          rows={2}
          value={form.descripcion}
          onChange={set('descripcion')}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div>
          <label className="label">
            {form.precio_incluye_igv ? 'Precio unitario (con IGV)' : 'Precio unitario (sin IGV)'}
          </label>
          <div style={{ position: 'relative' }}>
            <span style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', fontWeight: 700, color: '#94A3B8', fontFamily: 'var(--font-mono)', fontSize: '13px', pointerEvents: 'none' }}>S/</span>
            <input
              required
              type="number"
              step="0.01"
              min="0"
              className="input"
              style={{ paddingLeft: '34px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
              value={form.precio_unitario}
              onChange={set('precio_unitario')}
            />
          </div>
          {showPreview && (
            <div style={{ marginTop: '8px', fontSize: '12px', color: '#64748B', lineHeight: 1.5 }}>
              <div>
                Base sin IGV: <strong style={{ color: '#0F172A' }}>S/ {formatCurrency(precioBase)}</strong>
              </div>
              <div>
                Precio final: <strong style={{ color: '#2563EB' }}>S/ {formatCurrency(precioFinal)}</strong>
              </div>
            </div>
          )}
        </div>
        <div>
          <label className="label">Modo de registro</label>
          <CustomSelect
            value={form.precio_incluye_igv ? 'con_igv' : 'sin_igv'}
            onChange={(value) =>
              setForm((current) => ({ ...current, precio_incluye_igv: value === 'con_igv' }))
            }
            options={[
              { value: 'con_igv', label: 'Con IGV' },
              { value: 'sin_igv', label: 'Sin IGV' },
            ]}
          />
        </div>
        <div>
          <label className="label">Unidad (U.M.)</label>
          <CustomSelect
            value={form.unidad_medida}
            onChange={(v) => setForm((c) => ({ ...c, unidad_medida: v }))}
            options={[
              { value: 'NIU', label: 'NIU — Unidad' },
              { value: 'ZZ',  label: 'ZZ — Servicio' },
              { value: 'KGM', label: 'KGM — Kilogramo' },
              { value: 'MTR', label: 'MTR — Metro' },
              { value: 'MIL', label: 'MIL — Millar' },
            ]}
          />
        </div>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '6px' }}>
            <label className="label" style={{ margin: 0 }}>Codigo SKU</label>
            <button
              type="button"
              className="label-action-btn"
              onClick={() => set('codigo_interno')({ target: { value: `SKU-${Math.random().toString(36).slice(2,6).toUpperCase()}` } })}
            >
              <RefreshCw style={{ width: '10px', height: '10px' }} /> Generar
            </button>
          </div>
          <input
            className="input"
            style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, textTransform: 'uppercase' }}
            value={form.codigo_interno}
            onChange={set('codigo_interno')}
            placeholder="Ej. IMP-A4-FC"
          />
        </div>
      </div>

      <div className="modal-footer modal-footer--bleed">
        <button type="button" onClick={onCancel} className="btn-modal-cancel">
          Cancelar
        </button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving ? <Spinner size="sm" /> : <Save className="h-4 w-4" />} Guardar
        </button>
      </div>
    </form>
  );
}

export default function ProductosPage() {
  const toast = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    svc.list()
      .then(setList)
      .catch(() => toast('Error al cargar productos', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const filtered = list.filter(
    (item) =>
      item.nombre?.toLowerCase().includes(search.toLowerCase()) ||
      item.codigo_interno?.toLowerCase().includes(search.toLowerCase()),
  );

  const handleSave = async (form) => {
    setSaving(true);
    try {
      const payload = { ...form, precio_unitario: Number(form.precio_unitario) };
      if (modal.mode === 'create') {
        await svc.create(payload);
        toast('Producto creado');
      } else {
        await svc.update(modal.item.id, payload);
        toast('Producto actualizado');
      }
      setModal(null);
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Eliminar este producto?')) return;
    try {
      await svc.remove(id);
      toast('Producto eliminado');
      load();
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <div className="page-header-copy">
          <p className="page-kicker">Catalogo reusable</p>
          <h2 className="page-title">Productos y servicios</h2>
          <p className="page-subtitle">{list.length} elementos listos para cotizaciones recurrentes.</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="ink-table-card" style={{ padding: '14px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div className="ink-search" style={{ maxWidth: '450px', flex: '1' }}>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
          <input
            className="input pl-9"
            placeholder="Buscar por nombre o codigo SKU..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setModal({ mode: 'create' })}>
          <Plus className="h-4 w-4" />
          Nuevo producto
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Sin productos"
          description="Agrega productos o servicios para acelerar tu operacion comercial."
          action={
            <button className="btn-primary" onClick={() => setModal({ mode: 'create' })}>
              Agregar producto
            </button>
          }
        />
      ) : (
        <div className="ink-table-card">
          <table className="ink-table">
            <thead>
              <tr>
                <th>Nombre y descripcion</th>
                <th>Codigo (SKU)</th>
                <th>U.M. SUNAT</th>
                <th className="text-right">Precio venta</th>
                <th className="text-right" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, idx) => {
                const dot = DOT_COLORS[idx % DOT_COLORS.length];
                const um = UM_COLORS[item.unidad_medida] || UM_DEFAULT;
                return (
                  <tr key={item.id}>
                    <td data-label="Nombre y descripcion">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: dot, flexShrink: 0 }} />
                        <span style={{ fontWeight: 700, color: '#0F172A', fontSize: '13px' }}>{item.nombre}</span>
                      </div>
                    </td>
                    <td data-label="Codigo (SKU)">
                      {item.codigo_interno
                        ? <span style={{ display: 'inline-block', padding: '2px 8px', background: '#F8FAFC', border: '1px solid #E2E8F0', color: '#475569', fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>{item.codigo_interno}</span>
                        : <span className="ink-empty-cell">--</span>
                      }
                    </td>
                    <td data-label="U.M. SUNAT">
                      <span style={{ display: 'inline-block', padding: '2px 6px', background: um.bg, border: `1px solid ${um.border}`, color: um.color, fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        {item.unidad_medida}
                      </span>
                    </td>
                    <td data-label="Precio venta" className="text-right">
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'baseline', gap: '3px' }}>
                          <span style={{ fontSize: '10px', fontWeight: 700, color: '#94A3B8' }}>S/</span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>
                            {formatCurrency(item.precio_unitario)}
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>
                          Base: S/ {formatCurrency(item.valor_unitario)}
                        </div>
                      </div>
                    </td>
                    <td data-label="Acciones">
                      <div className="ink-row-actions">
                        <button
                          className="ink-row-btn"
                          onClick={() => setModal({ mode: 'edit', item })}
                          title="Editar"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          className="ink-row-btn ink-row-btn--danger"
                          onClick={() => handleDelete(item.id)}
                          title="Eliminar"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="ink-table-footer">
            <span className="ink-table-count">
              Mostrando <strong>{filtered.length}</strong> de <strong>{list.length}</strong> productos
            </span>
          </div>
        </div>
      )}

      <Modal
        open={!!modal}
        onClose={() => setModal(null)}
        title={modal?.mode === 'create' ? 'Nuevo producto' : 'Editar producto'}
      >
        {modal && (
          <ProductoForm
            initial={modal.mode === 'edit' ? modal.item : EMPTY_FORM}
            onSave={handleSave}
            onCancel={() => setModal(null)}
            saving={saving}
          />
        )}
      </Modal>
    </div>
  );
}
