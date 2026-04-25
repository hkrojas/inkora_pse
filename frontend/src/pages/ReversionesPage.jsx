import { useState } from 'react';
import { api } from '../lib/utils/api';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import Modal from '../components/ui/Modal';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { Plus, Trash2 } from 'lucide-react';

const ESTADO_OPTS = [
  { value: '1', label: '1 – Aceptada por SUNAT' },
  { value: '2', label: '2 – Rechazada' },
  { value: '3', label: '3 – Baja solicitada' },
];

const TIPO_DOC_OPTS = [
  { value: '01', label: '01 – Factura' },
  { value: '03', label: '03 – Boleta de venta' },
  { value: '07', label: '07 – Nota de crédito' },
  { value: '08', label: '08 – Nota de débito' },
];

const EMPTY_DETALLE = { tipoDoc: '01', serieNro: '', estado: '1' };

function today() {
  return new Date().toISOString().slice(0, 10);
}

function buildCorrelativo(fecha) {
  const d = (fecha || today()).replace(/-/g, '');
  return `RR-${d}-${String(Math.floor(Math.random() * 90000) + 10000)}`;
}

export default function ReversionesPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ fechaEmision: today(), correlativo: buildCorrelativo(), detalles: [{ ...EMPTY_DETALLE }] });
  const [submitting, setSubmitting] = useState(false);
  const [resultados, setResultados] = useState([]);
  const { addToast } = useToast();

  const setInput = (key) => (e) => setForm((c) => ({ ...c, [key]: e.target.value }));

  const setDetalle = (i, key) => (e) =>
    setForm((c) => { const ds = [...c.detalles]; ds[i] = { ...ds[i], [key]: e.target.value }; return { ...c, detalles: ds }; });

  const setDetalleSelect = (i, key) => (val) =>
    setForm((c) => { const ds = [...c.detalles]; ds[i] = { ...ds[i], [key]: val }; return { ...c, detalles: ds }; });

  const addDetalle = () => setForm((c) => ({ ...c, detalles: [...c.detalles, { ...EMPTY_DETALLE }] }));
  const removeDetalle = (i) => setForm((c) => ({ ...c, detalles: c.detalles.filter((_, idx) => idx !== i) }));

  const handleOpen = () => {
    const t = today();
    setForm({ fechaEmision: t, correlativo: buildCorrelativo(t), detalles: [{ ...EMPTY_DETALLE }] });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        fechaEmision: form.fechaEmision,
        correlativo: form.correlativo.trim(),
        details: form.detalles.map((d) => ({
          tipoDoc: d.tipoDoc,
          serieNro: d.serieNro.trim(),
          estado: d.estado,
        })),
      };
      const res = await api.post('/reversiones/enviar', payload);
      setResultados((prev) => [{ ...res, _corr: form.correlativo, _fecha: form.fechaEmision, _ts: new Date().toLocaleString() }, ...prev]);
      addToast(
        res.sunatResponse?.ticket ? `Ticket: ${res.sunatResponse.ticket}` : 'Reversión enviada',
        'success',
      );
      setModalOpen(false);
    } catch (err) {
      addToast(err?.message || 'No se pudo enviar la reversión. Revisa los datos e inténtalo nuevamente.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Reversiones</h1>
          <p className="page-subtitle">Resumen de reversiones ante SUNAT · /reversion/send · Asíncrono con ticket</p>
        </div>
        <button className="btn-primary" onClick={handleOpen}>
          <Plus size={15} /> Nueva Reversión
        </button>
      </div>

      <div className="ink-inline-alert" style={{ marginBottom: 16 }}>
        <strong>Flujo asíncrono:</strong> El envío devuelve un <strong>ticket</strong>. Consultar con <code>/reversion/status?ticket=...&amp;ruc=...</code>
      </div>

      {resultados.length === 0 ? (
        <EmptyState title="Sin reversiones enviadas" description="Los resúmenes de reversiones enviados aparecerán aquí." />
      ) : (
        <div className="ink-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="ink-table">
            <thead>
              <tr>
                <th>Correlativo</th>
                <th>Fecha</th>
                <th>Ticket SUNAT</th>
                <th>Enviado</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {resultados.map((r, i) => (
                <tr key={i}>
                  <td data-label="Correlativo"><span className="font-mono-label">{r._corr}</span></td>
                  <td data-label="Fecha">{r._fecha}</td>
                  <td data-label="Ticket SUNAT"><span className="font-mono-label" style={{ fontSize: 11 }}>{r.sunatResponse?.ticket || '—'}</span></td>
                  <td data-label="Enviado" style={{ fontSize: 11 }}>{r._ts}</td>
                  <td data-label="Estado">
                    {r.sunatResponse?.success === false
                      ? <span style={{ color: 'var(--color-error)', fontWeight: 700, fontSize: 12 }}>RECHAZADO</span>
                      : r.sunatResponse?.ticket
                        ? <span style={{ color: 'var(--color-warning)', fontWeight: 700, fontSize: 12 }}>TICKET PENDIENTE</span>
                        : <span style={{ color: 'var(--color-success)', fontWeight: 700, fontSize: 12 }}>ENVIADO</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Nueva Reversión" size="md">
        <form onSubmit={handleSubmit} className="space-y-4">

          <div className="responsive-form-grid-1-2">
            <div>
              <label className="label">Fecha emisión <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" type="date" value={form.fechaEmision} onChange={setInput('fechaEmision')} required />
            </div>
            <div>
              <label className="label">Correlativo <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" value={form.correlativo} onChange={setInput('correlativo')} placeholder="RR-20260415-10001" required />
              <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>Formato: RR-YYYYMMDD-NNNNN</p>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 12 }}>
            <div className="responsive-form-section-header">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>
                Documentos a revertir
              </p>
              <button type="button" className="btn-ghost" onClick={addDetalle}>
                <Plus size={12} /> Agregar
              </button>
            </div>
            {form.detalles.map((d, i) => (
              <div key={i} className="responsive-form-grid-120-1-120-auto" style={{ border: '1px solid var(--border-subtle)', padding: 12, marginBottom: 8, background: 'var(--bg-surface-low)' }}>
                <div>
                  <label className="label" style={{ fontSize: 10 }}>Tipo doc</label>
                  <CustomSelect compact value={d.tipoDoc} onChange={setDetalleSelect(i, 'tipoDoc')} options={TIPO_DOC_OPTS} />
                </div>
                <div>
                  <label className="label" style={{ fontSize: 10 }}>Serie-Correlativo</label>
                  <input className="input" value={d.serieNro} onChange={setDetalle(i, 'serieNro')} placeholder="F001-000001" />
                </div>
                <div>
                  <label className="label" style={{ fontSize: 10 }}>Estado</label>
                  <CustomSelect compact value={d.estado} onChange={setDetalleSelect(i, 'estado')} options={ESTADO_OPTS} />
                </div>
                {form.detalles.length > 1 && (
                  <button type="button" onClick={() => removeDetalle(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-error)', padding: '8px 4px', alignSelf: 'flex-end' }}>
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="ink-inline-alert" style={{ fontSize: 12 }}>
            <strong>Endpoint:</strong> POST /reversion/send — Requiere consulta posterior con ticket + RUC emisor.
          </div>

          <div className="responsive-form-actions">
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting && <Spinner size={14} />}
              Enviar Reversión
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
