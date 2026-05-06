import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Download,
  Plus,
  RotateCcw,
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

const TIPO_DOC_OPTS = [
  { value: '20', label: '20 - Retencion' },
  { value: '40', label: '40 - Percepcion' },
];

const MOTIVO_OPTS = [
  { value: 'ERROR DE SISTEMA', label: 'Error de sistema' },
  { value: 'ERROR DE RUC', label: 'Error de RUC' },
  { value: 'ERROR EN DOCUMENTO', label: 'Error en documento' },
  { value: 'OPERACION NO REALIZADA', label: 'Operacion no realizada' },
];

const EMPTY_DETALLE = {
  tipoDoc: '20',
  serie: 'R001',
  correlativo: '',
  desMotivoBaja: 'ERROR DE SISTEMA',
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

function addDays(dateString, days) {
  const [year, month, day] = String(dateString || today()).split('-').map(Number);
  const value = new Date(year, month - 1, day);
  value.setDate(value.getDate() + days);
  return [
    value.getFullYear(),
    String(value.getMonth() + 1).padStart(2, '0'),
    String(value.getDate()).padStart(2, '0'),
  ].join('-');
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

function reversionTicket(reversion) {
  return reversion.ticket || reversion.sunatResponse?.ticket || reversion.sunat_response?.ticket || '';
}

function reversionDisplayNumber(reversion) {
  const fecha = onlyDate(reversion.fec_comunicacion || reversion._fecha).replace(/-/g, '');
  const correlativo = reversion.correlativo || reversion._corr || '';
  if (fecha && correlativo) return `RR-${fecha}-${correlativo}`;
  return correlativo || '-';
}

function getReversionStatus(reversion) {
  if (reversion.status) return reversion.status;
  if (reversion.sunatResponse?.success === false || reversion.sunat_response?.success === false) return 'rejected';
  if (reversion.sunatResponse?.ticket || reversion.sunat_response?.ticket) return 'pending';
  return 'sent';
}

function getReversionBadge(reversion) {
  const status = getReversionStatus(reversion);
  if (status === 'rejected') return <Badge variant="error">Rechazado</Badge>;
  if (status === 'pending') return <Badge variant="warning">Ticket pendiente</Badge>;
  return <Badge variant="success">Enviado</Badge>;
}

function defaultSerieForTipo(tipoDoc) {
  return tipoDoc === '40' ? 'P001' : 'R001';
}

export default function ReversionesPage() {
  const toast = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    fecGeneracion: today(),
    fecComunicacion: addDays(today(), 1),
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

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/reversiones/?limit=${PER_PAGE}`);
      setResultados(Array.isArray(res) ? res : []);
    } catch {
      toast('No se pudo cargar reversiones. Revisa tu conexion e intentalo nuevamente.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    setPage(1);
  }, [search, filters, activeTab]);

  const setInput = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));
  const setDetalle = (index, key) => (event) =>
    setForm((current) => {
      const detalles = [...current.detalles];
      detalles[index] = { ...detalles[index], [key]: event.target.value };
      return { ...current, detalles };
    });
  const setDetalleSelect = (index, key) => (value) =>
    setForm((current) => {
      const detalles = [...current.detalles];
      detalles[index] = {
        ...detalles[index],
        [key]: value,
        ...(key === 'tipoDoc' ? { serie: defaultSerieForTipo(value) } : {}),
      };
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
      fecComunicacion: addDays(fecha, 1),
      correlativo: buildCorrelativo(),
      detalles: [{ ...EMPTY_DETALLE }],
    });
    setModalOpen(true);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        fecGeneracion: toApiDate(form.fecGeneracion),
        fecComunicacion: toApiDate(form.fecComunicacion),
        correlativo: form.correlativo.trim(),
        details: form.detalles.map((detalle) => ({
          tipoDoc: detalle.tipoDoc,
          serie: detalle.serie.trim().toUpperCase(),
          correlativo: detalle.correlativo.trim(),
          desMotivoBaja: detalle.desMotivoBaja.trim().toUpperCase(),
        })),
      };
      const res = await api.post('/reversiones/enviar', payload);
      setResultados((prev) => [res, ...prev].slice(0, PER_PAGE));
      toast(res.ticket ? `Ticket: ${res.ticket}` : 'Reversion enviada correctamente', 'success');
      setModalOpen(false);
    } catch (err) {
      toast(err?.message || 'No se pudo enviar la reversion. Revisa los datos e intentalo nuevamente.', 'error');
      load();
    } finally {
      setSubmitting(false);
    }
  };

  const constrained = useMemo(
    () =>
      resultados.filter((reversion) => {
        const q = search.trim().toLowerCase();
        const fecha = onlyDate(reversion.fec_comunicacion || reversion._fecha);
        const correlativo = reversionDisplayNumber(reversion).toLowerCase();
        const ticket = reversionTicket(reversion).toLowerCase();
        const error = String(reversion.sunat_error || '').toLowerCase();
        const matchSearch = !q || correlativo.includes(q) || fecha.includes(q) || ticket.includes(q) || error.includes(q);
        const matchDesde = !filters.desde || fecha >= filters.desde;
        const matchHasta = !filters.hasta || fecha <= filters.hasta;
        return matchSearch && matchDesde && matchHasta;
      }),
    [resultados, search, filters],
  );

  const tabCounts = useMemo(() => {
    const base = { all: constrained.length, sent: 0, pending: 0, rejected: 0 };
    constrained.forEach((reversion) => {
      const key = getReversionStatus(reversion);
      if (base[key] !== undefined) base[key] += 1;
    });
    return base;
  }, [constrained]);

  const filtered = useMemo(
    () => constrained.filter((reversion) => activeTab === 'all' || getReversionStatus(reversion) === activeTab),
    [constrained, activeTab],
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const pageItems = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  const heroCards = [
    {
      key: 'all',
      value: constrained.length,
      label: 'Reversiones',
      text: `${constrained.length} registradas en esta vista`,
      link: 'Ver todos',
      icon: <RotateCcw size={16} />,
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
      label: 'Pendientes',
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
    <div className="page-shell page-shell--dense reversiones-page">
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
            Nueva reversion
          </button>
        </div>
      </div>

      <section className="attention document-list-hero ink-enter-2">
        <div className="attention-title document-list-hero-title">
          <div className="document-list-hero-head">
            <div className="attention-title-badge">
              <RotateCcw size={15} />
            </div>
          </div>

          <div className="document-list-hero-pagecopy">
            <h2>Reversiones</h2>
            <p>Resumen de reversiones de retenciones y percepciones ante SUNAT.</p>
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
            Mostrando <strong>{getVisibleRange(page, PER_PAGE, filtered.length)}</strong> de <strong>{filtered.length}</strong> reversiones
          </div>
        </div>

        {loading ? (
          <div className="document-list-loading">
            <Spinner size="lg" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="document-list-empty">
            <EmptyState
              icon={<RotateCcw size={22} />}
              title={
                hasActiveFilters
                  ? 'Sin resultados para estos filtros'
                  : activeTab !== 'all'
                    ? `No hay reversiones ${activeTab === 'sent' ? 'enviadas' : activeTab === 'pending' ? 'pendientes' : 'rechazadas'} en esta vista.`
                    : 'Aun no tienes reversiones enviadas'
              }
              description={
                hasActiveFilters
                  ? 'Ajusta las fechas para recuperar resultados.'
                  : activeTab === 'all'
                    ? 'Envia tu primera reversion para corregir retenciones o percepciones procesadas ante SUNAT.'
                    : 'Cuando existan reversiones en este estado apareceran aqui.'
              }
              action={
                hasActiveFilters ? (
                  <button className="btn-secondary" onClick={clearFilters}>
                    Limpiar filtros
                  </button>
                ) : (
                  <button className="btn-primary" onClick={handleOpen}>
                    <Plus size={15} />
                    Nueva reversion
                  </button>
                )
              }
            />
          </div>
        ) : (
          <div className="ink-table-card document-list-table">
            <div className="ink-table-header">
              <div className="ink-table-title">
                <strong>Reversiones enviadas</strong>
                <span>{filtered.length} visibles en esta vista</span>
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
              <table className="ink-table ink-reversion-table">
                <thead>
                  <tr>
                    <th>Correlativo</th>
                    <th>Comunicacion</th>
                    <th>Ticket SUNAT</th>
                    <th>Enviado</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((reversion) => {
                    const status = getReversionStatus(reversion);
                    const rowClass =
                      status === 'sent'
                        ? 'ink-table-row--accepted'
                        : status === 'pending'
                          ? 'ink-table-row--active'
                          : '';

                    return (
                      <tr key={reversion.id || reversionDisplayNumber(reversion)} className={rowClass}>
                        <td data-label="Correlativo">
                          <div className="ink-table-cell__primary document-list-folio">{reversionDisplayNumber(reversion)}</div>
                          <div className="ink-table-cell__meta">{reversion.details_count || 0} documentos</div>
                        </td>
                        <td data-label="Comunicacion">
                          <div className="ink-table-cell__primary">{formatDate(reversion.fec_comunicacion || reversion._fecha)}</div>
                          <div className="ink-table-cell__meta">Reversion</div>
                        </td>
                        <td data-label="Ticket SUNAT">
                          <div className="ink-table-cell__primary" style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                            {reversionTicket(reversion) || '-'}
                          </div>
                          {reversion.sunat_error && (
                            <div className="ink-table-cell__meta">{reversion.sunat_error}</div>
                          )}
                        </td>
                        <td data-label="Enviado">
                          <div className="ink-table-cell__meta">{formatDateTime(reversion.created_at || reversion._ts)}</div>
                        </td>
                        <td data-label="Estado">
                          {getReversionBadge(reversion)}
                        </td>
                      </tr>
                    );
                  })}
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
                <button type="button" className="page-btn active">
                  {page}
                </button>
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
        title="Nueva reversion"
        subtitle="Corrige retenciones o percepciones y envia la solicitud a SUNAT."
        icon={<RotateCcw size={22} />}
        footer={(
          <>
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" form="reversion-form" className="btn-primary" disabled={submitting}>
              {submitting && <Spinner size={14} />}
              Enviar reversion
            </button>
          </>
        )}
      >
        <form id="reversion-form" onSubmit={handleSubmit} className="drawer-editor-form">
          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header">
              <p>Cabecera de envio</p>
            </div>
            <p className="drawer-editor-section-intro">
              APISPeru espera correlativo numerico, fecha de generacion y fecha de comunicacion.
            </p>
            <div className="responsive-form-grid-1-1-2">
              <div>
                <label className="label">Fecha generacion <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" type="date" value={form.fecGeneracion} onChange={setInput('fecGeneracion')} required />
              </div>
              <div>
                <label className="label">Fecha comunicacion <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" type="date" value={form.fecComunicacion} onChange={setInput('fecComunicacion')} required />
              </div>
              <div>
                <label className="label">Correlativo <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.correlativo} onChange={setInput('correlativo')} placeholder="00001" required />
                <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                  Ingresa solo el numero. APISPeru arma el prefijo RR.
                </p>
              </div>
            </div>
          </div>

          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header responsive-form-section-header">
              <p>Documentos a revertir</p>
              <button type="button" className="btn-ghost drawer-editor-add" onClick={addDetalle}>
                <Plus size={12} /> Agregar
              </button>
            </div>
            <p className="drawer-editor-section-intro">
              Reversion aplica a retenciones tipo 20 y percepciones tipo 40, no a facturas ni boletas.
            </p>
            <div className="drawer-editor-list">
              {form.detalles.map((detalle, index) => (
                <div key={`${index}-${detalle.serie}`} className="drawer-editor-item">
                  <div className="responsive-form-grid-120-1-1-120-auto">
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Tipo doc</label>
                      <CustomSelect compact value={detalle.tipoDoc} onChange={setDetalleSelect(index, 'tipoDoc')} options={TIPO_DOC_OPTS} />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Serie</label>
                      <input className="input" value={detalle.serie} onChange={setDetalle(index, 'serie')} placeholder="R001" />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Correlativo doc.</label>
                      <input className="input" value={detalle.correlativo} onChange={setDetalle(index, 'correlativo')} placeholder="122" />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Motivo</label>
                      <CustomSelect compact value={detalle.desMotivoBaja} onChange={setDetalleSelect(index, 'desMotivoBaja')} options={MOTIVO_OPTS} />
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

          <div className="proto-alert info drawer-editor-note" style={{ fontSize: 12 }}>
            <strong>Contrato fiscal:</strong> POST /reversion/send con tipos 20/40, serie, correlativo y motivo de baja.
          </div>
        </form>
      </Drawer>
    </div>
  );
}
