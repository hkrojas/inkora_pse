import { useState } from 'react';
import { api } from '../lib/utils/api';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import Modal from '../components/ui/Modal';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { Plus, Trash2 } from 'lucide-react';

const ESTADO_OPTS = [
  { value: '1', label: '1 – Emitida' },
  { value: '2', label: '2 – Baja' },
  { value: '3', label: '3 – Corrección' },
];

const TIPO_DOC_CLIENTE_OPTS = [
  { value: '1', label: '1 – DNI' },
  { value: '4', label: '4 – Carnet extranjería' },
  { value: '6', label: '6 – RUC' },
  { value: '7', label: '7 – Pasaporte' },
  { value: '0', label: '0 – Sin doc.' },
];

const EMPTY_DETALLE = {
  tipoDoc: '03', serieNro: '', estado: '1',
  clienteTipo: '1', clienteNro: '',
  total: '', mtoOperGravadas: '', mtoIGV: '',
};

function today() {
  return new Date().toISOString().slice(0, 10);
}

function buildCorrelativo(fecha) {
  const d = (fecha || today()).replace(/-/g, '');
  return `RC-${d}-${String(Math.floor(Math.random() * 90000) + 10000)}`;
}

export default function ResumenDiarioPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ fecGeneracion: today(), fecResumen: today(), correlativo: buildCorrelativo(), detalles: [{ ...EMPTY_DETALLE }] });
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
    setForm({ fecGeneracion: t, fecResumen: t, correlativo: buildCorrelativo(t), detalles: [{ ...EMPTY_DETALLE }] });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        fecGeneracion: form.fecGeneracion,
        fecResumen: form.fecResumen,
        correlativo: form.correlativo.trim(),
        details: form.detalles.map((d) => ({
          tipoDoc: d.tipoDoc,
          serieNro: d.serieNro.trim(),
          estado: d.estado,
          clienteTipo: d.clienteTipo,
          clienteNro: d.clienteNro.trim() || '00000000',
          total: parseFloat(d.total) || 0,
          mtoOperGravadas: parseFloat(d.mtoOperGravadas) || 0,
          mtoIGV: parseFloat(d.mtoIGV) || 0,
        })),
      };
      const res = await api.post('/resumen-diario/enviar', payload);
      setResultados((prev) => [{ ...res, _corr: form.correlativo, _fecha: form.fecResumen, _ts: new Date().toLocaleString() }, ...prev]);
      addToast(
        res.sunatResponse?.ticket ? `Ticket: ${res.sunatResponse.ticket}` : 'Resumen enviado',
        'success',
      );
      setModalOpen(false);
    } catch (err) {
      addToast(err?.message || 'No se pudo enviar el resumen. Revisa los datos e inténtalo nuevamente.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Resumen Diario</h1>
          <p className="page-subtitle">Resumen de boletas del día · /summary/send · Asíncrono con ticket</p>
        </div>
        <button className="btn-primary" onClick={handleOpen}>
          <Plus size={15} /> Nuevo Resumen
        </button>
      </div>

      <div className="ink-inline-alert" style={{ marginBottom: 16 }}>
        <strong>Flujo asíncrono:</strong> El envío devuelve un <strong>ticket</strong>. Consultar con <code>/summary/status?ticket=...&amp;ruc=...</code>
      </div>

      {resultados.length === 0 ? (
        <EmptyState title="Sin resúmenes enviados" description="Los resúmenes diarios de boletas aparecerán aquí tras el envío." />
      ) : (
        <div className="ink-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="ink-table">
            <thead>
              <tr>
                <th>Correlativo</th>
                <th>Fecha resumen</th>
                <th>Ticket SUNAT</th>
                <th>Enviado</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {resultados.map((r, i) => (
                <tr key={i}>
                  <td data-label="Correlativo"><span className="font-mono-label">{r._corr}</span></td>
                  <td data-label="Fecha resumen">{r._fecha}</td>
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

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Nuevo Resumen Diario" size="lg">
        <form onSubmit={handleSubmit} className="space-y-4">

          <div className="responsive-form-grid-1-1-2">
            <div>
              <label className="label">Fecha generación <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" type="date" value={form.fecGeneracion} onChange={setInput('fecGeneracion')} required />
            </div>
            <div>
              <label className="label">Fecha resumen <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" type="date" value={form.fecResumen} onChange={setInput('fecResumen')} required />
            </div>
            <div>
              <label className="label">Correlativo <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" value={form.correlativo} onChange={setInput('correlativo')} placeholder="RC-20260415-10001" required />
              <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>Formato: RC-YYYYMMDD-NNNNN</p>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 12 }}>
            <div className="responsive-form-section-header">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>
                Boletas del resumen
              </p>
              <button type="button" className="btn-ghost" onClick={addDetalle}>
                <Plus size={12} /> Agregar boleta
              </button>
            </div>
            {form.detalles.map((d, i) => (
              <div key={i} style={{ border: '1px solid var(--border-subtle)', padding: 12, marginBottom: 8, background: 'var(--bg-surface-low)' }}>
                <div className="responsive-form-grid-1-90-120" style={{ marginBottom: 8 }}>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Serie-Correlativo (boleta)</label>
                    <input className="input" value={d.serieNro} onChange={setDetalle(i, 'serieNro')} placeholder="B001-000001" />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Estado</label>
                    <CustomSelect compact value={d.estado} onChange={setDetalleSelect(i, 'estado')} options={ESTADO_OPTS} />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Tipo doc cliente</label>
                    <CustomSelect compact value={d.clienteTipo} onChange={setDetalleSelect(i, 'clienteTipo')} options={TIPO_DOC_CLIENTE_OPTS} />
                  </div>
                </div>
                <div className="responsive-form-grid-1-1-1-1-auto">
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Nro doc cliente</label>
                    <input className="input" value={d.clienteNro} onChange={setDetalle(i, 'clienteNro')} placeholder="00000000" />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Total</label>
                    <input className="input" type="number" step="0.01" value={d.total} onChange={setDetalle(i, 'total')} placeholder="0.00" />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Base gravada</label>
                    <input className="input" type="number" step="0.01" value={d.mtoOperGravadas} onChange={setDetalle(i, 'mtoOperGravadas')} placeholder="0.00" />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>IGV</label>
                    <input className="input" type="number" step="0.01" value={d.mtoIGV} onChange={setDetalle(i, 'mtoIGV')} placeholder="0.00" />
                  </div>
                  {form.detalles.length > 1 && (
                    <button type="button" onClick={() => removeDetalle(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-error)', padding: '8px 4px', alignSelf: 'flex-end' }}>
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="ink-inline-alert" style={{ fontSize: 12 }}>
            <strong>Nota:</strong> El resumen diario tiene bloqueos conocidos en ApisPeru beta (error 2992). Usar en producción con cuenta activa.
          </div>

          <div className="responsive-form-actions">
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting && <Spinner size={14} />}
              Enviar Resumen
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
