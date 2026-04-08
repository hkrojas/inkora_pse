import { useState, useEffect } from 'react';
import { Plus, Eye } from 'lucide-react';
import { Link } from 'react-router-dom';
import { guias as svc } from '../services/guias';
import { cotizaciones as cotSvc } from '../services/cotizaciones';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Badge, { statusBadge } from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import { useToast } from '../components/ui/Toast';

function NuevaGuiaForm({ onSave, onCancel, saving }) {
  const [cotizaciones, setCotizaciones] = useState([]);
  const [form, setForm] = useState({
    cotizacion_id: '',
    fecha_traslado: new Date().toISOString().slice(0, 10),
    motivo_traslado: '01',
    descripcion_motivo: 'Venta',
    modalidad_traslado: '01',
    partida_ubigeo: '',
    partida_direccion: '',
    llegada_ubigeo: '',
    llegada_direccion: '',
    peso_bruto_total: '',
    unidad_medida_peso: 'KGM',
  });
  const [items, setItems] = useState([{ descripcion: '', cantidad: 1, unidad_medida: 'NIU' }]);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  useEffect(() => { cotSvc.list().then(setCotizaciones).catch(() => {}); }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      ...form,
      cotizacion_id: form.cotizacion_id ? Number(form.cotizacion_id) : null,
      peso_bruto_total: Number(form.peso_bruto_total),
      fecha_traslado: new Date(form.fecha_traslado).toISOString(),
      items: items.map((it) => ({ ...it, cantidad: Number(it.cantidad) })),
    });
  };

  const setItem = (i, k, v) => setItems((prev) => prev.map((it, idx) => idx === i ? { ...it, [k]: v } : it));

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Cotización de referencia</label>
          <select className="input" value={form.cotizacion_id} onChange={set('cotizacion_id')}>
            <option value="">Sin cotización</option>
            {cotizaciones.map((c) => <option key={c.id} value={c.id}>{c.internal_order_number || `#${c.id}`} — {c.cliente_nombre}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Fecha traslado *</label>
          <input required type="date" className="input" value={form.fecha_traslado} onChange={set('fecha_traslado')} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Motivo traslado</label>
          <select className="input" value={form.motivo_traslado} onChange={set('motivo_traslado')}>
            <option value="01">Venta</option>
            <option value="02">Compra</option>
            <option value="04">Traslado entre establecimientos</option>
            <option value="13">Otros</option>
          </select>
        </div>
        <div>
          <label className="label">Modalidad</label>
          <select className="input" value={form.modalidad_traslado} onChange={set('modalidad_traslado')}>
            <option value="01">Transporte público</option>
            <option value="02">Transporte privado</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Dirección partida *</label>
          <input required className="input" value={form.partida_direccion} onChange={set('partida_direccion')} />
        </div>
        <div>
          <label className="label">Dirección llegada *</label>
          <input required className="input" value={form.llegada_direccion} onChange={set('llegada_direccion')} />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="label">Ubigeo partida</label>
          <input className="input" value={form.partida_ubigeo} onChange={set('partida_ubigeo')} placeholder="150101" />
        </div>
        <div>
          <label className="label">Ubigeo llegada</label>
          <input className="input" value={form.llegada_ubigeo} onChange={set('llegada_ubigeo')} placeholder="150102" />
        </div>
        <div>
          <label className="label">Peso bruto (KGM) *</label>
          <input required type="number" step="0.001" className="input" value={form.peso_bruto_total} onChange={set('peso_bruto_total')} />
        </div>
      </div>
      {/* Items */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="label">Bienes a trasladar *</label>
          <button type="button" onClick={() => setItems((p) => [...p, { descripcion: '', cantidad: 1, unidad_medida: 'NIU' }])} className="text-xs text-blue-600 hover:underline">+ Línea</button>
        </div>
        {items.map((it, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-end">
            <div className="col-span-7">
              <input required className="input" placeholder="Descripción del bien" value={it.descripcion} onChange={(e) => setItem(i, 'descripcion', e.target.value)} />
            </div>
            <div className="col-span-2">
              <input required type="number" min="1" className="input" value={it.cantidad} onChange={(e) => setItem(i, 'cantidad', e.target.value)} />
            </div>
            <div className="col-span-2">
              <select className="input" value={it.unidad_medida} onChange={(e) => setItem(i, 'unidad_medida', e.target.value)}>
                <option value="NIU">Und</option>
                <option value="KGM">Kg</option>
                <option value="ZZ">Svc</option>
              </select>
            </div>
            <div className="col-span-1">
              {items.length > 1 && <button type="button" onClick={() => setItems((p) => p.filter((_, idx) => idx !== i))} className="text-gray-400 hover:text-red-500 text-lg">×</button>}
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">Cancelar</button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving && <Spinner size="sm" />} Crear guía
        </button>
      </div>
    </form>
  );
}

export default function GuiasPage() {
  const toast = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    svc.list().then(setList).catch(() => toast('Error al cargar guías', 'error')).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleSave = async (data) => {
    setSaving(true);
    try {
      await svc.create(data);
      toast('Guía creada');
      setModal(false);
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Guías de remisión</h1>
          <p className="text-sm text-gray-500">{list.length} guías</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setModal(true)}>
          <Plus className="h-4 w-4" /> Nueva guía
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : list.length === 0 ? (
        <EmptyState title="Sin guías" description="Crea tu primera guía de remisión" action={<button className="btn-primary" onClick={() => setModal(true)}>Nueva guía</button>} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Número</th>
                <th className="px-4 py-3">Fecha traslado</th>
                <th className="px-4 py-3">Origen</th>
                <th className="px-4 py-3">Destino</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {list.map((g) => (
                <tr key={g.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{g.serie}-{String(g.correlativo).padStart(6, '0')}</td>
                  <td className="px-4 py-3 text-gray-500">{g.fecha_traslado ? new Date(g.fecha_traslado).toLocaleDateString('es-PE') : '—'}</td>
                  <td className="px-4 py-3 text-gray-500 max-w-[140px] truncate">{g.partida_direccion}</td>
                  <td className="px-4 py-3 text-gray-500 max-w-[140px] truncate">{g.llegada_direccion}</td>
                  <td className="px-4 py-3">
                    <Badge variant={statusBadge(g.estado)}>{g.estado || 'pendiente'}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/guias/${g.id}`} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 inline-flex">
                      <Eye className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modal} onClose={() => setModal(false)} title="Nueva guía de remisión" size="xl">
        <NuevaGuiaForm onSave={handleSave} onCancel={() => setModal(false)} saving={saving} />
      </Modal>
    </div>
  );
}
