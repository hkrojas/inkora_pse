import { useEffect, useState } from 'react';
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock3,
  Download,
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
import Pagination from '../components/ui/Pagination';

const ESTADO_OPTS = [
  { value: '1', label: '1 - Emitida' },
  { value: '2', label: '2 - Baja' },
  { value: '3', label: '3 - Correccion' },
];

const TIPO_DOC_CLIENTE_OPTS = [
  { value: '1', label: '1 - DNI' },
  { value: '4', label: '4 - Carnet extranjeria' },
  { value: '6', label: '6 - RUC' },
  { value: '7', label: '7 - Pasaporte' },
  { value: '0', label: '0 - Sin doc.' },
];

const EMPTY_DETALLE = {
  tipoDoc: '03',
  serieNro: '',
  estado: '1',
  clienteTipo: '1',
  clienteNro: '',
  total: '',
  mtoOperGravadas: '',
  mtoIGV: '',
};

const PER_PAGE = 15;

const TAB_DEFS = [
  { key: 'all', label: 'Todos' },
  { key: 'sent', label: 'Enviados' },
  { key: 'pending', label: 'Pendientes' },
  { key: 'rejected', label: 'Rechazados' },
];

function today() {
  return new Date().toISOString().slice(0, 10);
}

function buildCorrelativo() {
  const now = new Date();
  const secondsOfDay = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
  return String(secondsOfDay).padStart(5, '0');
}

function toApiDate(dateString) {
  return dateString ? `${dateString}T00:00:00-05:00` : null;
}

function onlyDate(value) {
  return value ? String(value).slice(0, 10) : '';
}

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('es-PE');
}

function formatDateTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('es-PE');
}

function getVisibleRange(page, pageSize, total) {
  if (!total) return '0';
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return `${start}-${end}`;
}

function resumenTicket(resumen) {
  return resumen.ticket || resumen.sunatResponse?.ticket || resumen.sunat_response?.ticket || '';
}

function resumenDisplayNumber(resumen) {
  const fecha = onlyDate(resumen.fec_resumen || resumen._fecha).replace(/-/g, '');
  const correlativo = resumen.correlativo || resumen._corr || '';
  if (fecha && correlativo) return `RC-${fecha}-${correlativo}`;
  return correlativo || '-';
}

function getResumenStatus(resumen) {
  if (resumen.status) return resumen.status;
  if (resumen.sunatResponse?.success === false || resumen.sunat_response?.success === false) return 'rejected';
  if (resumen.sunatResponse?.ticket || resumen.sunat_response?.ticket) return 'pending';
  return 'sent';
}

function getResumenBadge(resumen) {
  const status = getResumenStatus(resumen);
  if (status === 'rejected') return <Badge variant="error">Rechazado</Badge>;
  if (status === 'pending') return <Badge variant="warning">Ticket pendiente</Badge>;
  return <Badge variant="success">Enviado</Badge>;
}

export default function ResumenDiarioPage() {
  const toast = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    fecGeneracion: today(),
    fecResumen: today(),
    correlativo: buildCorrelativo(),
    detalles: [{ ...EMPTY_DETALLE }],
  });
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
      const res = await api.get(`/resumen-diario/page?${params.toString()}`, { signal });
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
      toast('No se pudo cargar resumen diario. Revisa tu conexion e intentalo nuevamente.', 'error');
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

  const setInput = (key) => (e) => setForm((current) => ({ ...current, [key]: e.target.value }));
  const setDetalle = (index, key) => (e) =>
    setForm((current) => {
      const detalles = [...current.detalles];
      detalles[index] = { ...detalles[index], [key]: e.target.value };
      return { ...current, detalles };
    });
  const setDetalleSelect = (index, key) => (value) =>
    setForm((current) => {
      const detalles = [...current.detalles];
      detalles[index] = { ...detalles[index], [key]: value };
      return { ...current, detalles };
    });
  const addDetalle = () => setForm((current) => ({ ...current, detalles: [...current.detalles, { ...EMPTY_DETALLE }] }));
  const removeDetalle = (index) => setForm((current) => ({ ...current, detalles: current.detalles.filter((_, i) => i !== index) }));

  const setFilter = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }));

  const clearFilters = () => {
    setSearch('');
    setFilters({ desde: '', hasta: '' });
  };

  const hasActiveFilters = search || filters.desde || filters.hasta;

  const handleOpen = () => {
    const fecha = today();
    setForm({
      fecGeneracion: fecha,
      fecResumen: fecha,
      correlativo: buildCorrelativo(fecha),
      detalles: [{ ...EMPTY_DETALLE }],
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        fecGeneracion: toApiDate(form.fecGeneracion),
        fecResumen: toApiDate(form.fecResumen),
        correlativo: form.correlativo.trim(),
        moneda: 'PEN',
        details: form.detalles.map((detalle) => ({
          tipoDoc: detalle.tipoDoc,
          serieNro: detalle.serieNro.trim(),
          estado: detalle.estado,
          clienteTipo: detalle.clienteTipo,
          clienteNro: detalle.clienteNro.trim() || '00000000',
          total: Number.parseFloat(detalle.total) || 0,
          mtoOperGravadas: Number.parseFloat(detalle.mtoOperGravadas) || 0,
          mtoIGV: Number.parseFloat(detalle.mtoIGV) || 0,
        })),
      };
      const res = await api.post('/resumen-diario/enviar', payload);
      setResultados((prev) => [res, ...prev].slice(0, PER_PAGE));
      toast(res.ticket ? `Ticket: ${res.ticket}` : 'Resumen enviado correctamente', 'success');
      setModalOpen(false);
    } catch (err) {
      toast(err?.message || 'No se pudo enviar el resumen. Revisa los datos e intentalo nuevamente.', 'error');
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
      label: 'Resumenes visibles',
      text: `${tabCounts.all} registrados`,
      link: 'Ver todos',
      icon: <BarChart3 size={16} />,
    },
    {
      key: 'sent',
      value: tabCounts.sent,
      label: 'Enviados',
      text: tabCounts.sent ? 'Procesados correctamente' : 'Sin envios completados',
      link: 'Ver enviados',
      icon: <CheckCircle2 size={16} />,
    },
    {
      key: 'pending',
      value: tabCounts.pending,
      label: 'Pendientes de ticket',
      text: tabCounts.pending ? 'Requieren consulta SUNAT' : 'Sin tickets pendientes',
      link: 'Revisar pendientes',
      icon: <Clock3 size={16} />,
    },
    {
      key: 'rejected',
      value: tabCounts.rejected,
      label: 'Rechazados',
      text: tabCounts.rejected ? 'Necesitan correccion' : 'Sin rechazos registrados',
      link: 'Ver rechazados',
      icon: <XOctagon size={16} />,
    },
  ];

  return (
    <div className="page-shell page-shell--dense resumen-diario-page">
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
            Nuevo resumen
          </button>
        </div>
      </div>

      <section className="attention document-list-hero ink-enter-2">
        <div className="attention-title document-list-hero-title">
          <div className="document-list-hero-head">
            <div className="attention-title-badge">
              <BarChart3 size={15} />
            </div>
          </div>

          <div className="document-list-hero-pagecopy">
            <h2>Resumen diario</h2>
            <p>Consolidado de boletas del dia enviado de forma asincrona con ticket SUNAT.</p>
          </div>

          <div className="document-list-hero-kicker">
            Flujo asincrono - {tabCounts.pending ? `${tabCounts.pending} tickets por consultar` : 'Sin pendientes'}
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
              placeholder="Buscar por correlativo, fecha o ticket..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
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
            Mostrando <strong>{getVisibleRange(page, PER_PAGE, total)}</strong> de <strong>{total}</strong> resumenes
          </div>
        </div>

        {loading ? (
          <div className="document-list-loading">
            <Spinner size="lg" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="document-list-empty">
            <EmptyState
              icon={<BarChart3 size={22} />}
              title={
                hasActiveFilters
                  ? 'Sin resultados para estos filtros'
                  : activeTab !== 'all'
                    ? `No hay resumenes ${activeTab === 'sent' ? 'enviados' : activeTab === 'pending' ? 'pendientes' : 'rechazados'} en esta vista.`
                    : 'Aun no tienes resumenes diarios enviados'
              }
              description={
                hasActiveFilters
                  ? 'Ajusta las fechas para recuperar resultados.'
                  : activeTab === 'all'
                    ? 'Envia tu primer resumen diario para consolidar las boletas emitidas del dia ante SUNAT.'
                    : 'Cuando existan resumenes en este estado apareceran aqui.'
              }
              action={
                hasActiveFilters ? (
                  <button className="btn-secondary" onClick={clearFilters}>
                    Limpiar filtros
                  </button>
                ) : (
                  <button className="btn-primary" onClick={handleOpen}>
                    <Plus size={15} />
                    Nuevo resumen
                  </button>
                )
              }
            />
          </div>
        ) : (
          <div className="ink-table-card document-list-table">
            <div className="ink-table-header">
              <div className="ink-table-title">
                <strong>Resumenes diarios</strong>
                <span>{total} visibles en esta vista</span>
              </div>

              <div className="document-list-table-meta">
                <span className="document-list-table-pill">
                  <CheckCircle2 size={13} />
                  {tabCounts.sent} enviados
                </span>
                <span className="document-list-table-pill">
                  <Clock3 size={13} />
                  {tabCounts.pending} pendientes
                </span>
                <span className="document-list-table-pill">
                  <XOctagon size={13} />
                  {tabCounts.rejected} rechazados
                </span>
              </div>
            </div>

            <div className="ink-table-scroll">
              <table className="ink-table ink-summary-table">
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
                  {pageItems.map((resumen) => {
                    const status = getResumenStatus(resumen);
                    const rowClass =
                      status === 'sent'
                        ? 'ink-table-row--accepted'
                        : status === 'pending'
                          ? 'ink-table-row--active'
                          : '';

                    return (
                      <tr key={resumen.id || resumenDisplayNumber(resumen)} className={rowClass}>
                        <td data-label="Correlativo">
                          <div className="ink-table-cell__primary document-list-folio">{resumenDisplayNumber(resumen)}</div>
                          <div className="ink-table-cell__meta">{resumen.details_count || 0} comprobantes</div>
                        </td>
                        <td data-label="Fecha resumen">
                          <div className="ink-table-cell__primary">{formatDate(resumen.fec_resumen || resumen._fecha)}</div>
                          <div className="ink-table-cell__meta">{resumen.moneda || 'PEN'}</div>
                        </td>
                        <td data-label="Ticket SUNAT">
                          <div className="ink-table-cell__primary" style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                            {resumenTicket(resumen) || '-'}
                          </div>
                          {resumen.sunat_error && (
                            <div className="ink-table-cell__meta">{resumen.sunat_error}</div>
                          )}
                        </td>
                        <td data-label="Enviado">
                          <div className="ink-table-cell__meta">{formatDateTime(resumen.created_at || resumen._ts)}</div>
                        </td>
                        <td data-label="Estado">
                          {getResumenBadge(resumen)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="ink-table-footer">
              <span className="ink-table-count">
                Página <strong>{page}</strong> de <strong>{totalPages}</strong>
              </span>
              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} ariaLabel="Paginación del resumen diario" />
              <span className="ink-table-count">{PER_PAGE} por página</span>
            </div>
          </div>
        )}
      </article>

      <Drawer
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        variant="fiscal"
        eyebrow="Resumen SUNAT"
        status="Boletas del día"
        initialFocus="input, select, textarea"
        title="Nuevo resumen diario"
        subtitle="Consolida las boletas del dia y envia el resumen a SUNAT sin salir del listado."
        icon={<BarChart3 size={22} />}
        footer={(
          <>
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" form="resumen-diario-form" className="btn-primary" disabled={submitting}>
              {submitting && <Spinner size={14} />}
              Enviar resumen
            </button>
          </>
        )}
      >
        <form id="resumen-diario-form" onSubmit={handleSubmit} className="drawer-editor-form">
          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header">
              <p>Cabecera operativa</p>
            </div>
            <p className="drawer-editor-section-intro">
              Define la fecha de generacion, el corte del resumen y el correlativo numerico que enviara el proveedor fiscal.
            </p>
            <div className="responsive-form-grid-1-1-2">
              <div>
                <label className="label">Fecha generacion <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" type="date" value={form.fecGeneracion} onChange={setInput('fecGeneracion')} required />
              </div>
              <div>
                <label className="label">Fecha resumen <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" type="date" value={form.fecResumen} onChange={setInput('fecResumen')} required />
              </div>
              <div>
                <label className="label">Correlativo <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.correlativo} onChange={setInput('correlativo')} placeholder="00001" required />
                <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                  Ingresa solo el correlativo numerico. El proveedor fiscal arma el RC con la fecha.
                </p>
              </div>
            </div>
          </div>

          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header responsive-form-section-header">
              <p>Boletas del resumen</p>
              <button type="button" className="btn-ghost drawer-editor-add" onClick={addDetalle}>
                <Plus size={12} /> Agregar boleta
              </button>
            </div>
            <p className="drawer-editor-section-intro">
              Agrupa los comprobantes del dia con su estado, cliente y montos base para el consolidado.
            </p>
            <div className="drawer-editor-list">
              {form.detalles.map((detalle, index) => (
                <div key={`${index}-${detalle.serieNro}`} className="drawer-editor-item">
                  <div className="responsive-form-grid-1-90-120" style={{ marginBottom: 8 }}>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Serie-Correlativo</label>
                      <input className="input" value={detalle.serieNro} onChange={setDetalle(index, 'serieNro')} placeholder="B001-000001" />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Estado</label>
                      <CustomSelect compact value={detalle.estado} onChange={setDetalleSelect(index, 'estado')} options={ESTADO_OPTS} />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Tipo doc cliente</label>
                      <CustomSelect compact value={detalle.clienteTipo} onChange={setDetalleSelect(index, 'clienteTipo')} options={TIPO_DOC_CLIENTE_OPTS} />
                    </div>
                  </div>
                  <div className="responsive-form-grid-1-1-1-1-auto">
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Nro doc cliente</label>
                      <input className="input" value={detalle.clienteNro} onChange={setDetalle(index, 'clienteNro')} placeholder="00000000" />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Total</label>
                      <input className="input" type="number" step="0.01" value={detalle.total} onChange={setDetalle(index, 'total')} placeholder="0.00" />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Base gravada</label>
                      <input className="input" type="number" step="0.01" value={detalle.mtoOperGravadas} onChange={setDetalle(index, 'mtoOperGravadas')} placeholder="0.00" />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>IGV</label>
                      <input className="input" type="number" step="0.01" value={detalle.mtoIGV} onChange={setDetalle(index, 'mtoIGV')} placeholder="0.00" />
                    </div>
                    {form.detalles.length > 1 && (
                      <button type="button" className="drawer-editor-remove" onClick={() => removeDetalle(index)}>
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="proto-alert warning drawer-editor-note" style={{ fontSize: 12 }}>
            <strong>Nota:</strong> El resumen diario se guarda primero en Inkora y luego se marca como enviado o rechazado segun la respuesta del proveedor fiscal.
          </div>
        </form>
      </Drawer>
    </div>
  );
}
