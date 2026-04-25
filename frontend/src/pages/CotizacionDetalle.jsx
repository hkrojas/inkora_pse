import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, FileText, Plus, Receipt, Share2 } from 'lucide-react';
import { cotizaciones as svc } from '../services/cotizaciones';
import Spinner from '../components/ui/Spinner';
import Badge, { statusBadge } from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import CustomSelect from '../components/ui/CustomSelect';
import { useToast } from '../components/ui/Toast';

function PagoForm({ onSave, onCancel, saving }) {
  const [form, setForm] = useState({
    monto_pagado: '',
    metodo_pago: 'Yape',
    tipo: 'pago',
    referencia_operacion: '',
  });
  const set = (key) => (event) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSave({ ...form, monto_pagado: Number(form.monto_pagado) });
      }}
      className="space-y-4"
    >
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">Monto</label>
          <input
            required
            type="number"
            step="0.01"
            min="0.01"
            className="input"
            value={form.monto_pagado}
            onChange={set('monto_pagado')}
          />
        </div>
        <div>
          <label className="label">Metodo de pago</label>
          <CustomSelect
            value={form.metodo_pago}
            onChange={(v) => setForm((c) => ({ ...c, metodo_pago: v }))}
            options={['Yape', 'Efectivo', 'Transferencia', 'BCP', 'Interbank', 'BBVA', 'Tarjeta'].map((m) => ({ value: m, label: m }))}
          />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">Tipo</label>
          <CustomSelect
            value={form.tipo}
            onChange={(v) => setForm((c) => ({ ...c, tipo: v }))}
            options={[
              { value: 'adelanto', label: 'Adelanto' },
              { value: 'pago',     label: 'Pago final' },
            ]}
          />
        </div>
        <div>
          <label className="label">Referencia</label>
          <input
            className="input"
            value={form.referencia_operacion}
            onChange={set('referencia_operacion')}
            placeholder="Numero de operacion..."
          />
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">
          Cancelar
        </button>
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
  const [emitirModal, setEmitirModal] = useState(null); // '01' | '03' | null
  const [emitiendo, setEmitiendo] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([svc.get(id), svc.pagos(id)])
      .then(([cotizacionResponse, pagosResponse]) => {
        setCot(cotizacionResponse);
        setPagos(Array.isArray(pagosResponse) ? pagosResponse : []);
      })
      .catch(() => toast('No se pudo cargar la cotización. Revisa tu conexión e inténtalo nuevamente.', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const handleShare = async () => {
    try {
      const data = await svc.share(id);
      setShareUrl(data.url_compartir || data.url || data.public_url || '');
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  const handleEmitir = async () => {
    setEmitiendo(true);
    try {
      await svc.facturar(id, { tipo_comprobante: emitirModal });
      const label = emitirModal === '01' ? 'Factura' : 'Boleta';
      toast(`${label} emitida correctamente`);
      setEmitirModal(null);
      load();
    } catch (err) {
      toast(err.message || 'No se pudo emitir el comprobante. Revisa los datos e inténtalo nuevamente.', 'error');
    } finally {
      setEmitiendo(false);
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

  const fmt = (value) =>
    Number(value || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 });

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!cot) {
    return <div className="text-sm text-[var(--text-secondary)]">Cotizacion no encontrada.</div>;
  }

  return (
    <div className="page-shell max-w-6xl">
      <div className="page-header">
        <div className="page-header-copy">
          <Link to="/cotizaciones" className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <ArrowLeft className="h-4 w-4" />
            Volver a cotizaciones
          </Link>
          <p className="page-kicker">Detalle comercial</p>
          <h2 className="page-title">{cot.internal_order_number || `Cotizacion #${cot.id}`}</h2>
          <p className="page-subtitle">{cot.cliente_nombre || '--'}</p>
        </div>

        <div className="page-actions">
          <button onClick={handleShare} className="btn-secondary flex items-center gap-2">
            <Share2 className="h-4 w-4" />
            Compartir
          </button>
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/cotizaciones/${id}/pdf?redirect=1`}
            target="_blank"
            rel="noreferrer"
            className="btn-secondary flex items-center gap-2"
          >
            <FileText className="h-4 w-4" />
            PDF
          </a>
          {cot.document_kind === 'quotation' && cot.estado !== 'anulada' && !cot.linked_fiscal_document_id && (
            <>
              <button
                onClick={() => setEmitirModal('03')}
                className="btn-secondary flex items-center gap-2"
              >
                <Receipt className="h-4 w-4" />
                Emitir Boleta
              </button>
              <button
                onClick={() => setEmitirModal('01')}
                className="btn-primary flex items-center gap-2"
              >
                <Receipt className="h-4 w-4" />
                Emitir Factura
              </button>
            </>
          )}
          {cot.linked_fiscal_document_id && (
            <span style={{ fontSize: 12, color: 'var(--color-success)', fontFamily: 'var(--font-mono)', fontWeight: 700, padding: '0 8px' }}>
              ✓ {cot.linked_fiscal_document_number || 'Emitido'}
            </span>
          )}
        </div>
      </div>

      {shareUrl && (
        <div className="ink-inline-alert ink-inline-alert-info">
          <span className="flex-1 truncate font-mono-label text-xs">{shareUrl}</span>
          <a href={shareUrl} target="_blank" rel="noreferrer" className="btn-secondary flex items-center gap-2">
            Abrir
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      )}

      <div className="ink-metric-grid md:grid-cols-3">
        <div className="ink-metric-card">
          <p className="ink-metric-label">total</p>
          <p className="ink-metric-value">S/ {fmt(cot.total_venta)}</p>
          <p className="ink-metric-note">monto final de la cotizacion</p>
        </div>
        <div className="ink-metric-card">
          <p className="ink-metric-label">pagado</p>
          <p className="ink-metric-value text-[var(--color-success)]">S/ {fmt(cot.monto_pagado)}</p>
          <p className="ink-metric-note">pagos registrados en la plataforma</p>
        </div>
        <div className="ink-metric-card">
          <p className="ink-metric-label">saldo</p>
          <p className="ink-metric-value text-[var(--color-warning)]">S/ {fmt(cot.saldo_pendiente)}</p>
          <p className="ink-metric-note">importe pendiente por cobrar</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="ink-table-card">
          <div className="ink-card-header">
            <div>
              <h3 className="ink-card-title">Detalle</h3>
              <p className="ink-card-subtitle">Items incorporados a la cotizacion</p>
            </div>
          </div>

          <div className="grid gap-px bg-[var(--border-subtle)]">
            {(cot.items || []).map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between gap-4 bg-[var(--bg-surface)] px-5 py-4"
              >
                <div>
                  <p className="font-medium text-[var(--text-primary)]">{item.descripcion}</p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    {item.cantidad} × S/ {fmt(item.precio_unitario)}
                  </p>
                </div>
                <p className="font-mono-label text-sm">S/ {fmt(item.total_item)}</p>
              </div>
            ))}
          </div>

          <div className="border-t border-[var(--border-subtle)] px-5 py-4 text-right">
            <span className="text-sm text-[var(--text-secondary)]">IGV incluido · </span>
            <span className="font-mono-label text-sm text-[var(--text-primary)]">
              Total S/ {fmt(cot.total_venta)}
            </span>
          </div>
        </div>

        <div className="ink-table-card">
          <div className="ink-card-header">
            <div>
              <h3 className="ink-card-title">Pagos</h3>
              <p className="ink-card-subtitle">Registro de adelantos y pagos finales</p>
            </div>
            {cot.payment_status !== 'pagado' && (
              <button onClick={() => setPagoModal(true)} className="btn-secondary flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Registrar
              </button>
            )}
          </div>

          {pagos.length === 0 ? (
            <EmptyState title="Sin pagos registrados" description="Aun no se ha ingresado ningun pago para esta cotizacion." />
          ) : (
            <div className="grid gap-px bg-[var(--border-subtle)]">
              {pagos.map((pago) => (
                <div
                  key={pago.id}
                  className="flex items-center justify-between gap-4 bg-[var(--bg-surface)] px-5 py-4"
                >
                  <div>
                    <p className="font-mono-label text-sm">S/ {fmt(pago.monto_pagado)}</p>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">
                      {pago.metodo_pago} · {pago.tipo}
                    </p>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">
                    {pago.fecha_pago ? new Date(pago.fecha_pago).toLocaleDateString('es-PE') : '--'}
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-5 py-4">
            <Badge variant={statusBadge(cot.payment_status)}>
              {cot.payment_status || 'pendiente'}
            </Badge>
            <span className="font-mono-label text-xs text-[var(--text-secondary)]">
              Saldo S/ {fmt(cot.saldo_pendiente)}
            </span>
          </div>
        </div>
      </div>

      <Modal open={pagoModal} onClose={() => setPagoModal(false)} title="Registrar pago">
        <PagoForm onSave={handlePago} onCancel={() => setPagoModal(false)} saving={saving} />
      </Modal>

      <Modal
        open={!!emitirModal}
        onClose={() => !emitiendo && setEmitirModal(null)}
        title={emitirModal === '01' ? 'Emitir Factura Electrónica' : 'Emitir Boleta de Venta'}
        size="sm"
      >
        <div className="space-y-4">
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '12px 14px', background: 'var(--bg-surface-low)', border: '1px solid var(--border-subtle)' }}>
            <Receipt size={18} style={{ flexShrink: 0, marginTop: 2, color: 'var(--text-brand)' }} />
            <div>
              <p style={{ fontWeight: 700, fontSize: 13 }}>
                {cot?.internal_order_number || `Cotización #${id}`}
              </p>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                {cot?.cliente_nombre} · S/ {fmt(cot?.total_venta)}
              </p>
              <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                Se emitirá un comprobante tipo <strong>{emitirModal === '01' ? 'Factura (01)' : 'Boleta de Venta (03)'}</strong> ante SUNAT.
              </p>
            </div>
          </div>
          {emitirModal === '01' && (
            <div className="ink-inline-alert" style={{ fontSize: 12 }}>
              <strong>Factura:</strong> Requiere que el cliente tenga RUC válido configurado.
            </div>
          )}
          <div className="responsive-form-actions">
            <button className="btn-ghost" onClick={() => setEmitirModal(null)} disabled={emitiendo}>
              Cancelar
            </button>
            <button className="btn-primary" onClick={handleEmitir} disabled={emitiendo}>
              {emitiendo && <Spinner size={14} />}
              Confirmar emisión
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
