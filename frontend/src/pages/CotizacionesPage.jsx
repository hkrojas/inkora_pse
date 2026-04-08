import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Eye } from 'lucide-react';
import { cotizaciones as svc } from '../services/cotizaciones';
import { clientes as cliSvc } from '../services/clientes';
import { productos as prodSvc } from '../services/productos';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Badge, { statusBadge } from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import { useToast } from '../components/ui/Toast';

function NuevaCotizacionModal({ onSave, onCancel, saving }) {
  const [clientes, setClientes] = useState([]);
  const [productosDisp, setProductosDisp] = useState([]);
  const [clienteId, setClienteId] = useState('');
  const [moneda, setMoneda] = useState('PEN');
  const [tipoComprobante, setTipoComprobante] = useState('00');
  const [items, setItems] = useState([{ descripcion: '', cantidad: 1, precio_unitario: '' }]);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    Promise.all([cliSvc.list(), prodSvc.list()]).then(([c, p]) => {
      setClientes(c);
      setProductosDisp(p);
    }).finally(() => setLoadingData(false));
  }, []);

  const addItem = () => setItems((prev) => [...prev, { descripcion: '', cantidad: 1, precio_unitario: '' }]);
  const removeItem = (i) => setItems((prev) => prev.filter((_, idx) => idx !== i));
  const setItem = (i, k, v) => setItems((prev) => prev.map((it, idx) => idx === i ? { ...it, [k]: v } : it));

  const handleSelectProduct = (i, prodId) => {
    const p = productosDisp.find((x) => String(x.id) === String(prodId));
    if (p) setItems((prev) => prev.map((it, idx) => idx === i ? { ...it, descripcion: p.nombre, precio_unitario: p.precio_unitario } : it));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      cliente_id: Number(clienteId),
      moneda,
      tipo_comprobante: tipoComprobante,
      items: items.map((it) => ({
        descripcion: it.descripcion,
        cantidad: Number(it.cantidad),
        precio_unitario: Number(it.precio_unitario),
      })),
    });
  };

  if (loadingData) return <div className="flex justify-center py-8"><Spinner /></div>;

  const total = items.reduce((s, it) => s + (Number(it.cantidad) * Number(it.precio_unitario) || 0), 0);

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <label className="label">Cliente *</label>
          <select required className="input" value={clienteId} onChange={(e) => setClienteId(e.target.value)}>
            <option value="">Seleccionar cliente...</option>
            {clientes.map((c) => <option key={c.id} value={c.id}>{c.razon_social}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Moneda</label>
          <select className="input" value={moneda} onChange={(e) => setMoneda(e.target.value)}>
            <option value="PEN">PEN (S/)</option>
            <option value="USD">USD ($)</option>
          </select>
        </div>
      </div>

      <div>
        <label className="label">Tipo comprobante</label>
        <select className="input max-w-xs" value={tipoComprobante} onChange={(e) => setTipoComprobante(e.target.value)}>
          <option value="00">Cotización (sin comprobante)</option>
          <option value="01">Factura</option>
          <option value="03">Boleta</option>
        </select>
      </div>

      {/* Items */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="label">Items *</label>
          <button type="button" onClick={addItem} className="text-xs text-blue-600 hover:underline">+ Agregar línea</button>
        </div>
        <div className="space-y-2">
          {items.map((it, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-end">
              <div className="col-span-5">
                {i === 0 && <label className="label">Descripción</label>}
                <input
                  required
                  className="input"
                  placeholder="Descripción del servicio..."
                  value={it.descripcion}
                  onChange={(e) => setItem(i, 'descripcion', e.target.value)}
                />
              </div>
              <div className="col-span-3">
                {i === 0 && <label className="label">Producto (opcional)</label>}
                <select className="input text-xs" onChange={(e) => handleSelectProduct(i, e.target.value)} defaultValue="">
                  <option value="">Desde catálogo...</option>
                  {productosDisp.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </select>
              </div>
              <div className="col-span-1">
                {i === 0 && <label className="label">Cant.</label>}
                <input required type="number" min="0.01" step="any" className="input" value={it.cantidad} onChange={(e) => setItem(i, 'cantidad', e.target.value)} />
              </div>
              <div className="col-span-2">
                {i === 0 && <label className="label">Precio unit.</label>}
                <input required type="number" min="0.01" step="0.01" className="input" value={it.precio_unitario} onChange={(e) => setItem(i, 'precio_unitario', e.target.value)} />
              </div>
              <div className="col-span-1 flex justify-end">
                {items.length > 1 && (
                  <button type="button" onClick={() => removeItem(i)} className="text-gray-400 hover:text-red-500 text-lg leading-none">×</button>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 text-right text-sm font-semibold text-gray-900">
          Total: S/ {total.toLocaleString('es-PE', { minimumFractionDigits: 2 })}
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">Cancelar</button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving && <Spinner size="sm" />} Crear cotización
        </button>
      </div>
    </form>
  );
}

export default function CotizacionesPage() {
  const toast = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    svc.list().then(setList).catch(() => toast('Error al cargar cotizaciones', 'error')).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const filtered = list.filter((c) =>
    c.cliente_nombre?.toLowerCase().includes(search.toLowerCase()) ||
    String(c.id).includes(search) ||
    c.internal_order_number?.toLowerCase().includes(search.toLowerCase())
  );

  const handleSave = async (data) => {
    setSaving(true);
    try {
      await svc.create(data);
      toast('Cotización creada');
      setModal(false);
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const fmt = (n) => Number(n || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 });

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Cotizaciones</h1>
          <p className="text-sm text-gray-500">{list.length} cotizaciones</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setModal(true)}>
          <Plus className="h-4 w-4" /> Nueva cotización
        </button>
      </div>

      <div className="mb-4 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input className="input pl-9 max-w-sm" placeholder="Buscar por cliente, número..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <EmptyState title="Sin cotizaciones" description="Crea tu primera cotización" action={<button className="btn-primary" onClick={() => setModal(true)}>Nueva cotización</button>} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">N° Orden</th>
                <th className="px-4 py-3">Cliente</th>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3">Estado pago</th>
                <th className="px-4 py-3">Estado doc.</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.internal_order_number || `#${c.id}`}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{c.cliente_nombre || '—'}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {c.fecha_emision ? new Date(c.fecha_emision).toLocaleDateString('es-PE') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">S/ {fmt(c.total_venta)}</td>
                  <td className="px-4 py-3">
                    <Badge variant={statusBadge(c.payment_status)}>{c.payment_status || 'pendiente'}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={statusBadge(c.estado)}>{c.estado || '—'}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/cotizaciones/${c.id}`} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 inline-flex">
                      <Eye className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modal} onClose={() => setModal(false)} title="Nueva cotización" size="xl">
        <NuevaCotizacionModal onSave={handleSave} onCancel={() => setModal(false)} saving={saving} />
      </Modal>
    </div>
  );
}
