import { useEffect, useState } from 'react';
import { api } from '../lib/utils/api';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import Modal from '../components/ui/Modal';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { FieldError } from '../components/ui/FieldError';
import ConfirmEmitDialog from '../components/documents/ConfirmEmitDialog';
import { DocumentTypeBadge } from '../components/documents/DocumentType';
import { formatCurrency, MOTIVOS_NC, MOTIVOS_ND } from '../lib/utils/documents';
import { Plus } from 'lucide-react';

const TIPO_NOTA_OPTS = [
  { value: 'credito', label: 'Nota de Crédito (07)' },
  { value: 'debito',  label: 'Nota de Débito (08)'  },
];

const EMPTY_FORM = {
  comprobante_afectado_id: '',
  tipo_nota: 'credito',
  cod_motivo: '',
  descripcion_motivo: '',
};

function estadoBadge(estado) {
  if (estado === 'facturada') return <Badge variant="success">Emitida</Badge>;
  if (estado === 'anulada')   return <Badge variant="danger">Anulada</Badge>;
  return <Badge variant="default">Pendiente</Badge>;
}

export default function NotasPage() {
  const [notas, setNotas]         = useState([]);
  const [facturas, setFacturas]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm]           = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [formErrors, setFormErrors]   = useState({});
  const { addToast } = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const [notasRes, facturasRes] = await Promise.all([
        api.get('/notas/'),
        api.get('/facturas-emitidas/'),
      ]);
      setNotas(notasRes);
      setFacturas(facturasRes.filter((f) => f.estado === 'facturada'));
    } catch {
      addToast('Error al cargar datos', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const motivosOpts = form.tipo_nota === 'credito' ? MOTIVOS_NC : MOTIVOS_ND;

  // Enriched options for comprobante afectado combobox
  const facturasOpts = facturas.map((f) => {
    const num = `${f.serie}-${String(f.correlativo).padStart(6, '0')}`;
    const cliente = f.cliente?.nombre || f.cliente?.razon_social || '';
    const total = formatCurrency(f.total_venta, f.moneda);
    const fecha = f.fecha_emision ? new Date(f.fecha_emision).toLocaleDateString('es-PE') : '';
    return {
      value: f.id,
      label: num,
      num,
      cliente,
      total,
      fecha,
      moneda: f.moneda,
      total_venta: f.total_venta,
      tipo_comprobante: f.tipo_comprobante,
      searchText: `${num} ${cliente}`,
    };
  });

  const selectedFactura = facturasOpts.find((f) => String(f.value) === String(form.comprobante_afectado_id));

  const validateForm = () => {
    const errs = {};
    if (!form.comprobante_afectado_id) errs.comprobante = 'Seleccione el comprobante afectado';
    if (!form.cod_motivo) errs.motivo = 'Seleccione el motivo';
    if (!form.descripcion_motivo.trim()) errs.descripcion = 'La descripción del motivo es obligatoria';
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleEmitClick = () => {
    if (!validateForm()) return;
    setConfirmOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await api.post('/notas/emitir', {
        comprobante_afectado_id: Number(form.comprobante_afectado_id),
        tipo_nota: form.tipo_nota,
        cod_motivo: form.cod_motivo,
        descripcion_motivo: form.descripcion_motivo.trim(),
      });
      addToast('Nota emitida correctamente', 'success');
      setConfirmOpen(false);
      setModalOpen(false);
      setForm(EMPTY_FORM);
      setFormErrors({});
      load();
    } catch (err) {
      addToast(err?.message || 'Error al emitir la nota', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const openModal = () => {
    setForm(EMPTY_FORM);
    setFormErrors({});
    setModalOpen(true);
  };

  const tipoNotaBadge = form.tipo_nota === 'credito' ? '07' : '08';

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">Notas de Crédito / Débito</h1>
          <p className="page-subtitle">Ajustes sobre comprobantes emitidos ante SUNAT</p>
        </div>
        <button className="btn-primary" onClick={openModal}>
          <Plus size={15} /> Nueva Nota
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}><Spinner size="lg" /></div>
      ) : notas.length === 0 ? (
        <EmptyState title="Sin notas emitidas" description="Las notas de crédito y débito aparecerán aquí una vez emitidas." />
      ) : (
        <div className="ink-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="ink-table">
            <thead>
              <tr>
                <th>Número</th>
                <th>Tipo</th>
                <th>Comprobante afectado</th>
                <th>Cliente</th>
                <th>Motivo</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {notas.map((n) => (
                <tr key={n.id}>
                  <td data-label="Numero">
                    <span className="font-mono-label">{n.serie}-{String(n.correlativo).padStart(6, '0')}</span>
                  </td>
                  <td data-label="Tipo">
                    <DocumentTypeBadge tipo={n.document_kind === 'credit_note' ? '07' : '08'} size="sm" />
                  </td>
                  <td data-label="Comprobante afectado">
                    <span className="font-mono-label">
                      {n.source_quote ? `${n.source_quote.serie}-${String(n.source_quote.correlativo).padStart(6, '0')}` : '—'}
                    </span>
                  </td>
                  <td data-label="Cliente">{n.cliente?.nombre || n.cliente?.razon_social || '—'}</td>
                  <td data-label="Motivo" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {n.nota_motivo_descripcion || '—'}
                  </td>
                  <td data-label="Estado">{estadoBadge(n.estado)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Form modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Nueva Nota de Crédito / Débito">
        <div className="space-y-4">

          {/* Tipo nota */}
          <div>
            <label className="label">Tipo de nota</label>
            <CustomSelect
              value={form.tipo_nota}
              onChange={(v) => setForm((c) => ({ ...c, tipo_nota: v, cod_motivo: '' }))}
              options={TIPO_NOTA_OPTS}
            />
          </div>

          {/* Comprobante afectado — enriched combobox */}
          <div>
            <label className="label">
              Comprobante afectado <span style={{ color: '#DC2626' }}>*</span>
            </label>
            <CustomSelect
              value={form.comprobante_afectado_id}
              onChange={(v) => { setForm((c) => ({ ...c, comprobante_afectado_id: v })); setFormErrors((e) => ({ ...e, comprobante: undefined })); }}
              options={facturasOpts}
              searchable
              searchPlaceholder="Buscar por número o cliente..."
              placeholder="Seleccionar factura o boleta..."
              filterOption={(opt, q) => opt.searchText?.toLowerCase().includes(q)}
              renderOption={(opt) => (
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', minWidth: 0 }}>
                  <div style={{ minWidth: 0 }}>
                    <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, color: '#4F46E5' }}>{opt.num}</p>
                    <p style={{ fontSize: '12px', color: '#0F172A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{opt.cliente}</p>
                    <p style={{ fontSize: '10px', color: '#94A3B8' }}>{opt.fecha}</p>
                  </div>
                  <p style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700, color: '#0F172A', flexShrink: 0 }}>{opt.total}</p>
                </div>
              )}
              renderPreview={(opt) => (
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700 }}>
                  {opt.num} · {opt.cliente}
                </span>
              )}
            />
            <FieldError message={formErrors.comprobante} />
            {selectedFactura && (
              <div style={{ marginTop: '6px', padding: '8px 12px', background: '#F8FAFC', border: '1px solid #E2E8F0', fontSize: '11px', color: '#475569', display: 'flex', gap: '16px' }}>
                <span><strong style={{ color: '#0F172A' }}>{selectedFactura.num}</strong></span>
                <span>{selectedFactura.cliente}</span>
                <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#0F172A' }}>{selectedFactura.total}</span>
              </div>
            )}
          </div>

          {/* Motivo */}
          <div>
            <label className="label">Motivo <span style={{ color: '#DC2626' }}>*</span></label>
            <CustomSelect
              value={form.cod_motivo}
              onChange={(v) => { setForm((c) => ({ ...c, cod_motivo: v })); setFormErrors((e) => ({ ...e, motivo: undefined })); }}
              options={motivosOpts}
              placeholder="Seleccionar motivo..."
            />
            <FieldError message={formErrors.motivo} />
          </div>

          {/* Descripción motivo */}
          <div>
            <label className="label">Descripción del motivo <span style={{ color: '#DC2626' }}>*</span></label>
            <input
              className="input"
              value={form.descripcion_motivo}
              onChange={(e) => { setForm((c) => ({ ...c, descripcion_motivo: e.target.value })); setFormErrors((e2) => ({ ...e2, descripcion: undefined })); }}
              placeholder="Ej: Devolución de mercadería por defecto"
            />
            <FieldError message={formErrors.descripcion} />
          </div>

          <div className="responsive-form-actions">
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="button" className="btn-primary" onClick={handleEmitClick}>
              Revisar y emitir nota
            </button>
          </div>
        </div>
      </Modal>

      {/* Confirm dialog */}
      <ConfirmEmitDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleSubmit}
        loading={submitting}
        mode="note"
        tipo={tipoNotaBadge}
        serie={selectedFactura ? `Afecta: ${selectedFactura.num}` : '—'}
        cliente={selectedFactura?.cliente || '—'}
        total={selectedFactura?.total_venta || 0}
        moneda={selectedFactura?.moneda || 'PEN'}
        extraLines={[
          `Motivo: ${motivosOpts.find((m) => m.value === form.cod_motivo)?.label || '—'}`,
          form.descripcion_motivo || '',
        ].filter(Boolean)}
      />
    </div>
  );
}
