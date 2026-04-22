import { useState } from 'react';
import { api } from '../lib/utils/api';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import Modal from '../components/ui/Modal';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { Plus, Trash2 } from 'lucide-react';

const REGIMEN_OPTS = [
  { value: '01', label: '01 – Tasa 3%' },
  { value: '02', label: '02 – Tasa 6%' },
];

const TIPO_DOC_OPTS = [
  { value: '01', label: '01 – Factura' },
  { value: '03', label: '03 – Boleta de venta' },
];

const EMPTY_DETALLE = {
  tipoDoc: '01', serieNro: '', fechaEmision: '',
  impTotalPagado: '', mtoBaseRet: '', mtoRetenido: '', fechaRet: '',
};

const EMPTY_FORM = {
  serie: '', correlativo: '', fechaEmision: '',
  clienteNumDoc: '', clienteRznSocial: '', clienteTipoDoc: '6',
  regResolucion: '01', periAgente: '', impTotalRet: '',
  detalles: [{ ...EMPTY_DETALLE }],
};

export default function RetencionesPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [resultados, setResultados] = useState([]);
  const { addToast } = useToast();

  const set = (key) => (val) => setForm((c) => ({ ...c, [key]: val }));
  const setInput = (key) => (e) => setForm((c) => ({ ...c, [key]: e.target.value }));

  const setDetalle = (i, key) => (e) =>
    setForm((c) => { const ds = [...c.detalles]; ds[i] = { ...ds[i], [key]: e.target.value }; return { ...c, detalles: ds }; });

  const setDetalleSelect = (i, key) => (val) =>
    setForm((c) => { const ds = [...c.detalles]; ds[i] = { ...ds[i], [key]: val }; return { ...c, detalles: ds }; });

  const addDetalle = () => setForm((c) => ({ ...c, detalles: [...c.detalles, { ...EMPTY_DETALLE }] }));
  const removeDetalle = (i) => setForm((c) => ({ ...c, detalles: c.detalles.filter((_, idx) => idx !== i) }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        tipoDoc: '20',
        serie: form.serie.trim(),
        correlativo: form.correlativo.trim(),
        fechaEmision: form.fechaEmision,
        client: { tipoDoc: form.clienteTipoDoc, numDoc: form.clienteNumDoc.trim(), rznSocial: form.clienteRznSocial.trim() },
        regResolucion: form.regResolucion,
        periAgente: form.periAgente.trim(),
        impTotalRet: parseFloat(form.impTotalRet) || 0,
        details: form.detalles.map((d) => ({
          tipoDoc: d.tipoDoc, serieNro: d.serieNro.trim(), fechaEmision: d.fechaEmision,
          impTotalPagado: parseFloat(d.impTotalPagado) || 0,
          mtoBaseRet: parseFloat(d.mtoBaseRet) || 0,
          mtoRetenido: parseFloat(d.mtoRetenido) || 0,
          fechaRet: d.fechaRet,
        })),
      };
      const res = await api.post('/retenciones/emitir', payload);
      setResultados((prev) => [{ ...res, _serie: form.serie, _correlativo: form.correlativo, _ts: new Date().toLocaleString() }, ...prev]);
      addToast('Retención emitida correctamente', 'success');
      setModalOpen(false);
      setForm(EMPTY_FORM);
    } catch (err) {
      addToast(err?.message || 'Error al emitir la retención', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Retenciones</h1>
          <p className="page-subtitle">Comprobantes de retención como agente retenedor · /retention/send</p>
        </div>
        <button className="btn-primary" onClick={() => { setForm(EMPTY_FORM); setModalOpen(true); }}>
          <Plus size={15} /> Nueva Retención
        </button>
      </div>

      {resultados.length === 0 ? (
        <EmptyState title="Sin retenciones registradas" description="Los comprobantes de retención emitidos aparecerán aquí." />
      ) : (
        <div className="ink-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="ink-table">
            <thead>
              <tr>
                <th>Serie-Correlativo</th>
                <th>Total Retenido</th>
                <th>Emitido</th>
                <th>SUNAT</th>
              </tr>
            </thead>
            <tbody>
              {resultados.map((r, i) => (
                <tr key={i}>
                  <td data-label="Serie-Correlativo"><span className="font-mono-label">{r._serie}-{r._correlativo}</span></td>
                  <td data-label="Total retenido">S/ {r.impTotalRet ?? '—'}</td>
                  <td data-label="Emitido" style={{ fontSize: 11 }}>{r._ts}</td>
                  <td data-label="SUNAT">
                    {r.sunatResponse?.success
                      ? <span style={{ color: 'var(--color-success)', fontWeight: 700, fontSize: 12 }}>ACEPTADO</span>
                      : <span style={{ color: 'var(--color-error)', fontWeight: 700, fontSize: 12 }}>RECHAZADO</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Nueva Retención" size="md">
        <form onSubmit={handleSubmit} className="space-y-4">

          <div className="responsive-form-grid-3">
            <div>
              <label className="label">Serie <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" value={form.serie} onChange={setInput('serie')} placeholder="R001" required />
            </div>
            <div>
              <label className="label">Correlativo <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" value={form.correlativo} onChange={setInput('correlativo')} placeholder="000001" required />
            </div>
            <div>
              <label className="label">Fecha emisión <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" type="date" value={form.fechaEmision} onChange={setInput('fechaEmision')} required />
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 12 }}>
            <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: 10 }}>
              Receptor (proveedor)
            </p>
            <div className="responsive-form-grid-120-1-2">
              <div>
                <label className="label">Tipo doc</label>
                <CustomSelect value={form.clienteTipoDoc} onChange={set('clienteTipoDoc')}
                  options={[{ value: '6', label: '6 – RUC' }, { value: '1', label: '1 – DNI' }]} />
              </div>
              <div>
                <label className="label">Número <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.clienteNumDoc} onChange={setInput('clienteNumDoc')} placeholder="20xxxxxxxxx" required />
              </div>
              <div>
                <label className="label">Razón social / Nombre <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.clienteRznSocial} onChange={setInput('clienteRznSocial')} placeholder="Nombre o razón social" required />
              </div>
            </div>
          </div>

          <div className="responsive-form-grid-3">
            <div>
              <label className="label">Régimen <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <CustomSelect value={form.regResolucion} onChange={set('regResolucion')} options={REGIMEN_OPTS} />
            </div>
            <div>
              <label className="label">Periodo agente</label>
              <input className="input" value={form.periAgente} onChange={setInput('periAgente')} placeholder="202401" />
            </div>
            <div>
              <label className="label">Total retenido <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input" type="number" step="0.01" value={form.impTotalRet} onChange={setInput('impTotalRet')} placeholder="0.00" required />
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 12 }}>
            <div className="responsive-form-section-header">
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-tertiary)' }}>
                Documentos relacionados
              </p>
              <button type="button" className="btn-ghost" onClick={addDetalle}>
                <Plus size={12} /> Agregar
              </button>
            </div>
            {form.detalles.map((d, i) => (
              <div key={i} style={{ border: '1px solid var(--border-subtle)', padding: 12, marginBottom: 8, background: 'var(--bg-surface-low)' }}>
                <div className="responsive-form-grid-100-1-120-1" style={{ marginBottom: 8 }}>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Tipo doc</label>
                    <CustomSelect compact value={d.tipoDoc} onChange={setDetalleSelect(i, 'tipoDoc')} options={TIPO_DOC_OPTS} />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Serie-Correlativo</label>
                    <input className="input" value={d.serieNro} onChange={setDetalle(i, 'serieNro')} placeholder="F001-000001" />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Fecha emisión</label>
                    <input className="input" type="date" value={d.fechaEmision} onChange={setDetalle(i, 'fechaEmision')} />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Fecha retención</label>
                    <input className="input" type="date" value={d.fechaRet} onChange={setDetalle(i, 'fechaRet')} />
                  </div>
                </div>
                <div className="responsive-form-grid-1-1-1-auto">
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Total pagado</label>
                    <input className="input" type="number" step="0.01" value={d.impTotalPagado} onChange={setDetalle(i, 'impTotalPagado')} placeholder="0.00" />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Base retención</label>
                    <input className="input" type="number" step="0.01" value={d.mtoBaseRet} onChange={setDetalle(i, 'mtoBaseRet')} placeholder="0.00" />
                  </div>
                  <div>
                    <label className="label" style={{ fontSize: 10 }}>Monto retenido</label>
                    <input className="input" type="number" step="0.01" value={d.mtoRetenido} onChange={setDetalle(i, 'mtoRetenido')} placeholder="0.00" />
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
            <strong>Endpoint:</strong> POST /retention/send — Respuesta inmediata · tipoDoc: 20
          </div>

          <div className="responsive-form-actions">
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting && <Spinner size={14} />}
              Emitir Retención
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
