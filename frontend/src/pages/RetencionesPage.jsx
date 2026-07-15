import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Download,
  HandCoins,
  Plus,
  Search,
  Trash2,
  XCircle,
  XOctagon,
} from 'lucide-react';
import { api } from '../lib/utils/api';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import Drawer from '../components/ui/Drawer';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';

const PER_PAGE = 15;
const RETENTION_RATE = 0.03;

const REGIMEN_OPTS = [
  { value: '01', label: '01 - Tasa 3%' },
];

const TIPO_DOC_OPTS = [
  { value: '01', label: '01 - Factura' },
  { value: '07', label: '07 - Nota de credito' },
  { value: '08', label: '08 - Nota de debito' },
];

const TAB_DEFS = [
  { key: 'all', label: 'Todos' },
  { key: 'sent', label: 'Aceptados' },
  { key: 'pending', label: 'Pendientes' },
  { key: 'rejected', label: 'Rechazados' },
];

function today() {
  return new Date().toISOString().slice(0, 10);
}

function buildCorrelativo() {
  const now = new Date();
  const secondsOfDay = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
  return String(secondsOfDay).padStart(6, '0');
}

function toApiDate(dateString) {
  return dateString ? `${dateString}T00:00:00-05:00` : null;
}

function toMoney(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Number(parsed.toFixed(2)) : 0;
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString('es-PE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('es-PE');
}

function getVisibleRange(page, pageSize, total) {
  if (!total) return '0';
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return `${start}-${end}`;
}

function createDetalle() {
  const fecha = today();
  return {
    tipoDoc: '01',
    numDoc: '',
    fechaEmision: fecha,
    fechaRetencion: fecha,
    moneda: 'PEN',
    impTotal: '',
    impPagar: '',
    impRetenido: '',
    pagoImporte: '',
    pagoFecha: fecha,
  };
}

function createForm() {
  return {
    serie: 'R001',
    correlativo: buildCorrelativo(),
    fechaEmision: today(),
    proveedorTipoDoc: '6',
    proveedorNumDoc: '',
    proveedorRznSocial: '',
    regimen: '01',
    tasa: '3.00',
    observacion: 'COMPROBANTE DE RETENCION',
    detalles: [createDetalle()],
  };
}

function getStatus(retencion) {
  if (retencion.status) return retencion.status;
  if (retencion.sunatResponse?.success === false || retencion.sunat_response?.success === false) return 'rejected';
  if (retencion.sunatResponse?.ticket || retencion.sunat_response?.ticket) return 'pending';
  return retencion.sunatResponse?.success ? 'sent' : 'pending';
}

function getStatusBadge(retencion) {
  const status = getStatus(retencion);
  if (status === 'rejected') return <Badge variant="error">Rechazado</Badge>;
  if (status === 'pending') return <Badge variant="warning">Pendiente</Badge>;
  return <Badge variant="success">Aceptado</Badge>;
}

function displayNumber(retencion) {
  const serie = retencion.serie || retencion._serie || 'R001';
  const correlativo = retencion.correlativo || retencion._correlativo || '';
  return correlativo ? `${serie}-${correlativo}` : serie;
}

export default function RetencionesPage() {
  const toast = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(createForm);
  const [submitting, setSubmitting] = useState(false);
  const [resultados, setResultados] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({ desde: '', hasta: '' });
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState('all');
  const [total, setTotal] = useState(0);
  const [serverCounts, setServerCounts] = useState({ all: 0, sent: 0, pending: 0, rejected: 0 });

  const load = async ({ signal } = {}) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * PER_PAGE),
        limit: String(PER_PAGE),
      });
      const q = search.trim();
      if (q) params.set('q', q);
      if (activeTab !== 'all') params.set('status', activeTab);
      if (filters.desde) params.set('desde', filters.desde);
      if (filters.hasta) params.set('hasta', filters.hasta);
      const res = await api.get(`/retenciones/page?${params.toString()}`, { signal });
      const items = Array.isArray(res) ? res : res.items || [];
      setResultados(items);
      setTotal(Array.isArray(res) ? items.length : Number(res.total || 0));
      setServerCounts({
        all: Number(res?.counts?.all || 0),
        sent: Number(res?.counts?.sent || 0),
        pending: Number(res?.counts?.pending || 0),
        rejected: Number(res?.counts?.rejected || 0),
      });
    } catch (err) {
      if (err?.isCanceled) return;
      toast('No se pudo cargar retenciones. Revisa tu conexion e intentalo nuevamente.', 'error');
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const debounce = setTimeout(() => load({ signal: controller.signal }), 300);
    return () => {
      clearTimeout(debounce);
      controller.abort();
    };
  }, [page, search, filters.desde, filters.hasta, activeTab]);

  useEffect(() => {
    setPage(1);
  }, [search, filters, activeTab]);

  const setInput = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));
  const setField = (key) => (value) => setForm((current) => ({ ...current, [key]: value }));
  const setFilter = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }));

  const setDetalle = (index, key) => (event) => {
    const value = event.target.value;
    setForm((current) => {
      const detalles = [...current.detalles];
      const next = { ...detalles[index], [key]: value };
      if (key === 'impTotal' && !next.impRetenido) {
        const retained = toMoney(value) * RETENTION_RATE;
        const payable = Math.max(toMoney(value) - retained, 0);
        next.impRetenido = String(retained.toFixed(2));
        if (!next.impPagar) next.impPagar = String(payable.toFixed(2));
        if (!next.pagoImporte) next.pagoImporte = String(payable.toFixed(2));
      }
      if (key === 'impPagar' && !next.pagoImporte) {
        next.pagoImporte = value;
      }
      detalles[index] = next;
      return { ...current, detalles };
    });
  };

  const setDetalleSelect = (index, key) => (value) =>
    setForm((current) => {
      const detalles = [...current.detalles];
      detalles[index] = { ...detalles[index], [key]: value };
      return { ...current, detalles };
    });

  const addDetalle = () => setForm((current) => ({ ...current, detalles: [...current.detalles, createDetalle()] }));
  const removeDetalle = (index) => setForm((current) => ({ ...current, detalles: current.detalles.filter((_, i) => i !== index) }));

  const clearFilters = () => {
    setSearch('');
    setFilters({ desde: '', hasta: '' });
  };

  const hasActiveFilters = search || filters.desde || filters.hasta;

  const handleOpen = () => {
    setForm(createForm());
    setModalOpen(true);
  };

  const totals = useMemo(() => {
    return form.detalles.reduce(
      (acc, detalle) => {
        acc.impRetenido += toMoney(detalle.impRetenido);
        acc.impPagado += toMoney(detalle.impPagar);
        return acc;
      },
      { impRetenido: 0, impPagado: 0 },
    );
  }, [form.detalles]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        serie: form.serie.trim().toUpperCase(),
        correlativo: form.correlativo.trim(),
        fechaEmision: toApiDate(form.fechaEmision),
        proveedor: {
          tipoDoc: form.proveedorTipoDoc,
          numDoc: form.proveedorNumDoc.trim(),
          rznSocial: form.proveedorRznSocial.trim(),
        },
        regimen: form.regimen,
        tasa: toMoney(form.tasa || 3),
        impRetenido: totals.impRetenido,
        impPagado: totals.impPagado,
        observacion: form.observacion.trim() || undefined,
        details: form.detalles.map((detalle) => ({
          tipoDoc: detalle.tipoDoc,
          numDoc: detalle.numDoc.trim().toUpperCase(),
          fechaEmision: toApiDate(detalle.fechaEmision),
          impTotal: toMoney(detalle.impTotal),
          moneda: detalle.moneda,
          pagos: [
            {
              moneda: detalle.moneda,
              importe: toMoney(detalle.pagoImporte || detalle.impPagar),
              fecha: toApiDate(detalle.pagoFecha || detalle.fechaRetencion),
            },
          ],
          fechaRetencion: toApiDate(detalle.fechaRetencion),
          impRetenido: toMoney(detalle.impRetenido),
          impPagar: toMoney(detalle.impPagar),
          tipoCambio: {
            fecha: toApiDate(detalle.fechaRetencion),
            factor: 1,
            monedaObj: detalle.moneda,
            monedaRef: detalle.moneda,
          },
        })),
      };

      const res = await api.post('/retenciones/emitir', payload);
      setResultados((prev) => [res, ...prev].slice(0, PER_PAGE));
      toast(res.ticket ? `Ticket: ${res.ticket}` : 'Retencion emitida correctamente', 'success');
      setModalOpen(false);
    } catch (err) {
      toast(err?.message || 'No se pudo emitir la retencion. Revisa los datos e intentalo nuevamente.', 'error');
      load();
    } finally {
      setSubmitting(false);
    }
  };

  const tabCounts = serverCounts;
  const filtered = resultados;
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const pageItems = resultados;

  const heroCards = [
    {
      key: 'all',
      value: tabCounts.all,
      label: 'Retenciones',
      text: `${tabCounts.all} registradas`,
      link: 'Ver todos',
      icon: <HandCoins size={16} />,
    },
    {
      key: 'sent',
      value: tabCounts.sent,
      label: 'Aceptados',
      text: tabCounts.sent ? 'Aceptados por SUNAT' : 'Sin aceptados',
      link: 'Ver aceptados',
      icon: <CheckCircle2 size={16} />,
    },
    {
      key: 'rejected',
      value: tabCounts.rejected,
      label: 'Rechazados',
      text: tabCounts.rejected ? 'Necesitan correccion' : 'Sin rechazos',
      link: 'Ver rechazados',
      icon: <XOctagon size={16} />,
    },
  ];

  return (
    <div className="page-shell page-shell--dense retenciones-page">
      <div className="page-head ink-enter-1">
        <div className="page-actions document-list-page-actions">
          <button
            type="button"
            className="btn"
            onClick={() => toast('La exportacion esta en desarrollo.', 'info')}
          >
            <Download size={15} />
            Exportar
          </button>
          <button className="btn-primary" onClick={handleOpen}>
            <Plus size={15} />
            Nueva retencion
          </button>
        </div>
      </div>

      <section className="attention document-list-hero ink-enter-2">
        <div className="attention-title document-list-hero-title">
          <div className="document-list-hero-head">
            <div className="attention-title-badge">
              <HandCoins size={15} />
            </div>
          </div>

          <div className="document-list-hero-pagecopy">
            <h2>Retenciones</h2>
            <p>Comprobantes de retencion como agente retenedor ante SUNAT.</p>
          </div>

          <div className="document-list-hero-kicker">
            Tipo 20 - Tasa 3%
          </div>
        </div>

        {heroCards.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`attention-card document-list-hero-card${activeTab === item.key ? ' is-active' : ''}`}
            onClick={() => setActiveTab(item.key)}
          >
            <div className="document-list-hero-card-icon">{item.icon}</div>
            <strong>{item.value}</strong>
            <div className="attention-card-text">
              {item.label}
              <span>{item.text}</span>
            </div>
            <span className="attention-card-link">
              {item.link}
              <ArrowRight size={13} />
            </span>
          </button>
        ))}
      </section>

      <article className="panel document-list-panel ink-enter-3">
        <div className="toolbar">
          <label className="search-box">
            <Search size={16} />
            <input
              placeholder="Buscar por serie, correlativo o proveedor..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>

          <div className="toolbar-actions">
            {hasActiveFilters && (
              <button type="button" className="btn-ghost" onClick={clearFilters}>
                <XCircle size={15} />
                Limpiar filtros
              </button>
            )}
          </div>
        </div>

        <div className="document-list-filters">
          <div className="document-list-filter">
            <span>Desde</span>
            <DatePicker compact value={filters.desde} onChange={(value) => setFilter('desde', value)} />
          </div>
          <div className="document-list-filter">
            <span>Hasta</span>
            <DatePicker compact value={filters.hasta} onChange={(value) => setFilter('hasta', value)} />
          </div>
        </div>

        <div className="segments-row">
          <div className="segments">
            {TAB_DEFS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                className={`segment ${activeTab === key ? 'active' : ''}`}
                onClick={() => setActiveTab(key)}
              >
                {label}
                <span className="document-list-segment-count">{tabCounts[key] || 0}</span>
              </button>
            ))}
          </div>
          <div className="sort-text">
            Mostrando <strong>{getVisibleRange(page, PER_PAGE, total)}</strong> de{' '}
            <strong>{total}</strong> retenciones
          </div>
        </div>

        {loading ? (
          <div className="document-list-loading">
            <Spinner size={22} />
            Cargando retenciones...
          </div>
        ) : filtered.length === 0 ? (
          <div className="document-list-empty">
            <EmptyState
              icon={<HandCoins size={22} />}
              title={hasActiveFilters ? 'Sin resultados para estos filtros' : 'Aun no tienes retenciones emitidas'}
              description={
                hasActiveFilters
                  ? 'Ajusta la busqueda o el rango de fechas.'
                  : 'Emite la primera retencion usando datos validados para el proveedor fiscal/SUNAT.'
              }
              action={
                hasActiveFilters ? (
                  <button className="btn-secondary" onClick={clearFilters}>
                    Limpiar filtros
                  </button>
                ) : (
                  <button className="btn-primary" onClick={handleOpen}>
                    <Plus size={15} />
                    Nueva retencion
                  </button>
                )
              }
            />
          </div>
        ) : (
          <div className="ink-table-card document-list-table">
            <div className="ink-table-header">
              <div className="ink-table-title">
                <strong>Retenciones emitidas</strong>
                <span>{total} visibles en esta vista</span>
              </div>

              <div className="document-list-table-meta">
                <span className="document-list-table-pill">
                  <CheckCircle2 size={13} />
                  {tabCounts.sent} aceptadas
                </span>
                <span className="document-list-table-pill">
                  <Clock3 size={13} />
                  {tabCounts.pending} pendientes
                </span>
                <span className="document-list-table-pill">
                  <XOctagon size={13} />
                  {tabCounts.rejected} rechazadas
                </span>
              </div>
            </div>

            <div className="ink-table-scroll">
              <table className="ink-table ink-retencion-table">
                <thead>
                  <tr>
                    <th>Numero</th>
                    <th>Proveedor</th>
                    <th>Fecha</th>
                    <th>Total retenido</th>
                    <th>Pagado neto</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((retencion) => (
                    <tr key={retencion.id || displayNumber(retencion)}>
                      <td data-label="Numero">
                        <div className="ink-table-cell__primary document-list-folio">{displayNumber(retencion)}</div>
                        <div className="ink-table-cell__meta">Tipo 20 - Retencion</div>
                      </td>
                      <td data-label="Proveedor">
                        <div className="ink-table-cell__primary">{retencion.proveedor_rzn_social || '-'}</div>
                        <div className="ink-table-cell__meta">{retencion.proveedor_num_doc || '-'}</div>
                      </td>
                      <td data-label="Fecha">
                        <div className="ink-table-cell__primary">{formatDate(retencion.fecha_emision)}</div>
                      </td>
                      <td data-label="Total retenido">
                        <div className="ink-table-cell__primary" style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                          S/ {formatMoney(retencion.imp_retenido)}
                        </div>
                      </td>
                      <td data-label="Pagado neto">
                        <div className="ink-table-cell__primary" style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                          S/ {formatMoney(retencion.imp_pagado)}
                        </div>
                      </td>
                      <td data-label="Estado">
                        {getStatusBadge(retencion)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="ink-table-footer">
              <span className="ink-table-count">
                Pag. <strong>{page}</strong> de <strong>{totalPages}</strong>
              </span>
              <div className="pagination">
                <button
                  type="button"
                  className="page-btn"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                >
                  &#8249;
                </button>
                <button type="button" className="page-btn active">{page}</button>
                <button
                  type="button"
                  className="page-btn"
                  disabled={page >= totalPages}
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                >
                  &#8250;
                </button>
              </div>
              <span className="ink-table-count">{PER_PAGE} por pagina</span>
            </div>
          </div>
        )}
      </article>

      <Drawer
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        variant="fiscal"
        eyebrow="Comprobante fiscal"
        status="Retención"
        initialFocus="select, input, textarea"
        title="Nueva retencion"
        subtitle="Registra un comprobante tipo 20 con los campos exigidos por el proveedor fiscal y SUNAT."
        icon={<HandCoins size={22} />}
        footer={(
          <>
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" form="retencion-form" className="btn-primary" disabled={submitting}>
              {submitting && <Spinner size={14} />}
              Emitir retencion
            </button>
          </>
        )}
      >
        <form id="retencion-form" onSubmit={handleSubmit} className="drawer-editor-form">
          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header">
              <p>Cabecera fiscal</p>
            </div>
            <p className="drawer-editor-section-intro">
              SUNAT usa el comprobante tipo 20. La serie debe iniciar con R y el regimen vigente es 01 - tasa 3%.
            </p>
            <div className="responsive-form-grid-3">
              <div>
                <label className="label">Serie <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.serie} onChange={setInput('serie')} placeholder="R001" required maxLength={4} />
              </div>
              <div>
                <label className="label">Correlativo <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.correlativo} onChange={setInput('correlativo')} placeholder="000001" required maxLength={8} />
              </div>
              <div>
                <label className="label">Fecha emision <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" type="date" value={form.fechaEmision} onChange={setInput('fechaEmision')} required />
              </div>
            </div>
          </div>

          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header">
              <p>Proveedor sujeto a retencion</p>
            </div>
            <p className="drawer-editor-section-intro">
              Para este flujo se exige RUC. No se aceptan DNI ni documentos sin identificacion tributaria.
            </p>
            <div className="responsive-form-grid-120-1-2">
              <div>
                <label className="label">Tipo doc</label>
                <CustomSelect value={form.proveedorTipoDoc} onChange={setField('proveedorTipoDoc')} options={[{ value: '6', label: '6 - RUC' }]} />
              </div>
              <div>
                <label className="label">RUC <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.proveedorNumDoc} onChange={setInput('proveedorNumDoc')} placeholder="20xxxxxxxxx" required maxLength={11} />
              </div>
              <div>
                <label className="label">Razon social <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.proveedorRznSocial} onChange={setInput('proveedorRznSocial')} placeholder="Proveedor SAC" required maxLength={180} />
              </div>
            </div>
          </div>

          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header">
              <p>Regimen y resumen</p>
            </div>
            <div className="responsive-form-grid-3">
              <div>
                <label className="label">Regimen <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <CustomSelect value={form.regimen} onChange={setField('regimen')} options={REGIMEN_OPTS} />
              </div>
              <div>
                <label className="label">Tasa</label>
                <input className="input" value={form.tasa} onChange={setInput('tasa')} readOnly />
              </div>
              <div>
                <label className="label">Observacion</label>
                <input className="input" value={form.observacion} onChange={setInput('observacion')} maxLength={250} />
              </div>
            </div>
            <div className="proto-alert info drawer-editor-note" style={{ fontSize: 12 }}>
              Total retenido: <strong>S/ {formatMoney(totals.impRetenido)}</strong> - Pagado neto:{' '}
              <strong>S/ {formatMoney(totals.impPagado)}</strong>
            </div>
          </div>

          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header responsive-form-section-header">
              <p>Documentos relacionados</p>
              <button type="button" className="btn-ghost drawer-editor-add" onClick={addDetalle}>
                <Plus size={12} /> Agregar
              </button>
            </div>
            <p className="drawer-editor-section-intro">
              El proveedor fiscal espera numDoc con formato SERIE-CORRELATIVO y al menos un pago asociado.
            </p>
            <div className="drawer-editor-list">
              {form.detalles.map((detalle, index) => (
                <div key={index} className="drawer-editor-item">
                  <div className="responsive-form-grid-100-1-120-120" style={{ marginBottom: 8 }}>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Tipo doc</label>
                      <CustomSelect compact value={detalle.tipoDoc} onChange={setDetalleSelect(index, 'tipoDoc')} options={TIPO_DOC_OPTS} />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Serie-correlativo</label>
                      <input className="input" value={detalle.numDoc} onChange={setDetalle(index, 'numDoc')} placeholder="F001-123" required maxLength={13} />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>F. emision</label>
                      <input className="input" type="date" value={detalle.fechaEmision} onChange={setDetalle(index, 'fechaEmision')} required />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>F. retencion</label>
                      <input className="input" type="date" value={detalle.fechaRetencion} onChange={setDetalle(index, 'fechaRetencion')} required />
                    </div>
                  </div>

                  <div className="responsive-form-grid-1-1-1-auto">
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Total comprobante</label>
                      <input className="input" type="number" step="0.01" value={detalle.impTotal} onChange={setDetalle(index, 'impTotal')} placeholder="0.00" required />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Importe a pagar</label>
                      <input className="input" type="number" step="0.01" value={detalle.impPagar} onChange={setDetalle(index, 'impPagar')} placeholder="0.00" required />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Monto retenido</label>
                      <input className="input" type="number" step="0.01" value={detalle.impRetenido} onChange={setDetalle(index, 'impRetenido')} placeholder="0.00" required />
                    </div>
                    {form.detalles.length > 1 && (
                      <button type="button" className="drawer-editor-remove" onClick={() => removeDetalle(index)}>
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>

                  <div className="responsive-form-grid-3" style={{ marginTop: 8 }}>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Moneda</label>
                      <CustomSelect compact value={detalle.moneda} onChange={setDetalleSelect(index, 'moneda')} options={[{ value: 'PEN', label: 'PEN' }, { value: 'USD', label: 'USD' }]} />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Pago registrado</label>
                      <input className="input" type="number" step="0.01" value={detalle.pagoImporte} onChange={setDetalle(index, 'pagoImporte')} placeholder="0.00" required />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Fecha pago</label>
                      <input className="input" type="date" value={detalle.pagoFecha} onChange={setDetalle(index, 'pagoFecha')} required />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="proto-alert info drawer-editor-note" style={{ fontSize: 12 }}>
            <strong>Endpoint:</strong> POST /retention/send - tipoDoc SUNAT 20 - regimen 01 tasa 3%.
          </div>
        </form>
      </Drawer>
    </div>
  );
}
