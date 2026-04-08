import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FileText, Share2, Plus, ExternalLink } from 'lucide-react';
import { cotizaciones as svc } from '../services/cotizaciones';
import Spinner from '../components/ui/Spinner';
import Badge, { statusBadge } from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import { useToast } from '../components/ui/Toast';

function PagoForm({ onSave, onCancel, saving }) {
  const [form, setForm] = useState({ monto_pagado: '', metodo_pago: 'Yape', tipo: 'pago', referencia_operacion: '' });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSave({ ...form, monto_pagado: Number(form.monto_pagado) }); }} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Monto (S/) *</label>
          <input required type="number" step="0.01" min="0.01" className="input" value={form.monto_pagado} onChange={set('monto_pagado')} />
        </div>
        <div>
          <label className="label">Método de pago</label>
          <select className="input" value={form.metodo_pago} onChange={set('metodo_pago')}>
            {['Yape', 'Efectivo', 'Transferencia', 'BCP', 'Interbank', 'BBVA', 'Tarjeta'].map((m) => <option key={m}>{m}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Tipo</label>
          <select className="input" value={form.tipo} onChange={set('tipo')}>
            <option value="adelanto">Adelanto</option>
            <option value="pago">Pago final</option>
          </select>
        </div>
        <div>
          <label className="label">Referencia op.</label>
          <input className="input" value={form.referencia_operacion} onChange={set('referencia_operacion')} placeholder="Nº operación..." />
        </div>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">Cancelar</button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving && <Spinner size="sm" />} Registrar pago
        </button>
      </div>
    </form>
  );
}

export default function CotizacionDetalle() {
  const { id } = useParams();
  const toast = useToast();
  const [cot, setCot] = useState(null);
  const [pagos, setPagos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [shareUrl, setShareUrl] = useState('');
  const [pagoModal, setPagoModal] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([svc.get(id), svc.pagos(id)])
      .then(([c, p]) => { setCot(c); setPagos(Array.isArray(p) ? p : []); })
      .catch(() => toast('Error al cargar cotización', 'error'))
      .finally(() => setLoading(false));
  };
  useEffect(load, [id]);

  const handleShare = async () => {
    try {
      const data = await svc.share(id);
      setShareUrl(data.url || data.public_url || '');
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  const handlePago = async (data) => {
    setSaving(true);
    try {
      await svc.addPago(id, data);
      toast('Pago registrado');
      setPagoModal(false);
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const fmt = (n) => Number(n || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 });

  if (loading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  if (!cot) return <div className="p-6 text-sm text-gray-500">Cotización no encontrada.</div>;

  return (
    <div className="p-6 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <Link to="/cotizaciones" className="mb-3 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeft className="h-4 w-4" /> Volver
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">{cot.internal_order_number || `Cotización #${cot.id}`}</h1>
            <p className="text-sm text-gray-500">{cot.cliente_nombre || '—'}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={handleShare} className="btn-secondary flex items-center gap-2 text-sm">
              <Share2 className="h-4 w-4" /> Compartir
            </button>
            <a href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/cotizaciones/${id}/pdf`} target="_blank" rel="noreferrer" className="btn-secondary flex items-center gap-2 text-sm">
              <FileText className="h-4 w-4" /> PDF
            </a>
          </div>
        </div>
        {shareUrl && (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-blue-50 px-4 py-2.5 text-sm">
            <span className="flex-1 truncate font-mono text-blue-700">{shareUrl}</span>
            <a href={shareUrl} target="_blank" rel="noreferrer" className="shrink-0 text-blue-600 hover:underline flex items-center gap-1">
              Abrir <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500 mb-1">Total</p>
          <p className="text-xl font-bold text-gray-900">S/ {fmt(cot.total_venta)}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500 mb-1">Pagado</p>
          <p className="text-xl font-bold text-green-700">S/ {fmt(cot.monto_pagado)}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500 mb-1">Saldo</p>
          <p className="text-xl font-bold text-orange-600">S/ {fmt(cot.saldo_pendiente)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Items */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-5 py-3.5">
            <h2 className="text-sm font-semibold text-gray-900">Detalle</h2>
          </div>
          <div className="divide-y divide-gray-50">
            {(cot.items || []).map((it, i) => (
              <div key={i} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{it.descripcion}</p>
                  <p className="text-xs text-gray-500">{it.cantidad} × S/ {fmt(it.precio_unitario)}</p>
                </div>
                <p className="text-sm font-semibold text-gray-900">S/ {fmt(it.total_item)}</p>
              </div>
            ))}
          </div>
          <div className="border-t border-gray-100 px-5 py-3 text-right">
            <span className="text-xs text-gray-500">IGV incluido · </span>
            <span className="text-sm font-bold text-gray-900">Total S/ {fmt(cot.total_venta)}</span>
          </div>
        </div>

        {/* Pagos */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3.5">
            <h2 className="text-sm font-semibold text-gray-900">Pagos</h2>
            {cot.payment_status !== 'pagado' && (
              <button onClick={() => setPagoModal(true)} className="flex items-center gap-1 text-xs text-blue-600 hover:underline">
                <Plus className="h-3.5 w-3.5" /> Registrar
              </button>
            )}
          </div>
          {pagos.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-gray-400">Sin pagos registrados</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {pagos.map((p) => (
                <div key={p.id} className="flex items-center justify-between px-5 py-3">
                  <div>
                    <p className="text-sm font-medium text-gray-900">S/ {fmt(p.monto_pagado)}</p>
                    <p className="text-xs text-gray-500">{p.metodo_pago} · {p.tipo}</p>
                  </div>
                  <p className="text-xs text-gray-400">
                    {p.fecha_pago ? new Date(p.fecha_pago).toLocaleDateString('es-PE') : '—'}
                  </p>
                </div>
              ))}
            </div>
          )}
          <div className="border-t border-gray-100 px-5 py-3 flex items-center justify-between">
            <Badge variant={statusBadge(cot.payment_status)}>{cot.payment_status || 'pendiente'}</Badge>
            <span className="text-xs text-gray-500">Saldo S/ {fmt(cot.saldo_pendiente)}</span>
          </div>
        </div>
      </div>

      <Modal open={pagoModal} onClose={() => setPagoModal(false)} title="Registrar pago">
        <PagoForm onSave={handlePago} onCancel={() => setPagoModal(false)} saving={saving} />
      </Modal>
    </div>
  );
}
