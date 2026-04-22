import { useEffect, useState } from 'react';
import { api } from '../lib/utils/api';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import Modal from '../components/ui/Modal';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { XCircle, AlertTriangle } from 'lucide-react';

const MOTIVO_OPTS = [
  { value: 'ERROR_EN_EL_RUC', label: 'Error en el RUC del receptor' },
  { value: 'ERROR_EN_LA_DESCRIPCION', label: 'Error en la descripción' },
  { value: 'OPERACION_NO_REALIZADA', label: 'Operación no realizada' },
  { value: 'OTROS', label: 'Otros' },
];

export default function BajasPage() {
  const [facturas, setFacturas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [motivo, setMotivo] = useState('ERROR_EN_EL_RUC');
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get('/facturas-emitidas/');
      setFacturas(res.filter((f) => f.estado === 'facturada'));
    } catch {
      addToast('Error al cargar facturas', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleOpen = (factura) => {
    setSelected(factura);
    setMotivo('ERROR_EN_EL_RUC');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/bajas/anular', { comprobante_id: selected.id, motivo });
      addToast(`${selected.serie}-${String(selected.correlativo).padStart(6, '0')} enviado para baja`, 'success');
      setModalOpen(false);
      load();
    } catch (err) {
      addToast(err?.message || 'Error al procesar la baja', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Comunicación de Bajas</h1>
          <p className="page-subtitle">Anulación de comprobantes ante SUNAT · /voided/send · Asíncrono con ticket</p>
        </div>
      </div>

      <div className="ink-inline-alert" style={{ marginBottom: 16 }}>
        <strong>Flujo asíncrono:</strong> La baja genera un <strong>ticket</strong>. Consultar resultado con <code>/voided/status?ticket=...&amp;ruc=...</code>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <Spinner size="lg" />
        </div>
      ) : facturas.length === 0 ? (
        <EmptyState
          title="Sin facturas o boletas emitidas"
          description="Solo aparecen documentos en estado &quot;facturada&quot; que pueden ser anulados."
        />
      ) : (
        <div className="ink-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="ink-table">
            <thead>
              <tr>
                <th>Número</th>
                <th>Tipo</th>
                <th>Cliente</th>
                <th>Total</th>
                <th>Estado</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {facturas.map((f) => (
                <tr key={f.id}>
                  <td data-label="Numero"><span className="font-mono-label">{f.serie}-{String(f.correlativo).padStart(6, '0')}</span></td>
                  <td data-label="Tipo">{f.tipo_comprobante === '01' ? 'Factura' : f.tipo_comprobante === '03' ? 'Boleta' : f.tipo_comprobante}</td>
                  <td data-label="Cliente">{f.cliente?.nombre || f.cliente?.razon_social || '—'}</td>
                  <td data-label="Total"><span className="font-mono-label">{f.moneda === 'USD' ? '$' : 'S/'} {Number(f.total_venta || 0).toFixed(2)}</span></td>
                  <td data-label="Estado"><Badge variant="success">Emitida</Badge></td>
                  <td data-label="Accion">
                    <button
                      className="btn-danger"
                      onClick={() => handleOpen(f)}
                    >
                      <XCircle size={12} /> Dar de baja
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Confirmar Comunicación de Baja">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '12px 14px', background: '#FFF7ED', border: '1.5px solid #F97316' }}>
              <AlertTriangle size={18} style={{ color: '#F97316', flexShrink: 0, marginTop: 2 }} />
              <div>
                <p style={{ fontWeight: 700, fontSize: 13, color: '#0F172A' }}>
                  {selected.serie}-{String(selected.correlativo).padStart(6, '0')}
                </p>
                <p style={{ fontSize: 12, color: '#475569', marginTop: 2 }}>
                  {selected.cliente?.nombre || selected.cliente?.razon_social} ·{' '}
                  {selected.moneda === 'USD' ? '$' : 'S/'} {Number(selected.total_venta || 0).toFixed(2)}
                </p>
                <p style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>
                  Esta acción notificará a SUNAT que el documento debe ser anulado. Es irreversible.
                </p>
              </div>
            </div>

            <div>
              <label className="label">Motivo de la baja <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <CustomSelect value={motivo} onChange={setMotivo} options={MOTIVO_OPTS} />
            </div>

            <div className="ink-inline-alert" style={{ fontSize: 12 }}>
              <strong>Campos enviados:</strong> fecha generación, fecha comunicación (hoy), correlativo RA-YYYYMMDD-NNNNN, tipoDoc + serie + correlativo del comprobante, motivo.
            </div>

            <div className="responsive-form-actions">
              <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
              <button type="submit" className="btn-danger" disabled={submitting}>
                {submitting ? <Spinner size={14} /> : <XCircle size={14} />}
                Confirmar Baja
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
