import { useEffect, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Download,
  FileText,
  Plus,
  RefreshCw,
  Search,
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
import ConfirmEmitDialog from '../components/documents/ConfirmEmitDialog';
import { DocumentTypeBadge } from '../components/documents/DocumentType';
import { getSunatStatus, formatCurrency } from '../lib/utils/documents';

const MOTIVO_OPTS = [
  { value: 'ERROR_EN_EL_RUC', label: 'Error en el RUC del receptor' },
  { value: 'ERROR_EN_LA_DESCRIPCION', label: 'Error en la descripcion' },
  { value: 'OPERACION_NO_REALIZADA', label: 'Operacion no realizada' },
  { value: 'OTROS', label: 'Otros' },
];

const TIPO_FILTER_OPTS = [
  { value: 'all', label: 'Todos' },
  { value: '01', label: 'Facturas (01)' },
  { value: '03', label: 'Boletas (03)' },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'facturada', label: 'Emitida' },
  { value: 'anulada', label: 'Anulada' },
];

const PER_PAGE = 15;

const TAB_DEFS = [
  { key: 'all', label: 'Todos' },
  { key: 'emitida', label: 'Emitidas' },
  { key: 'anulada', label: 'Anuladas' },
];

function getVisibleRange(page, pageSize, total) {
  if (!total) return '0';
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return `${start}-${end}`;
}

function canVoidDocument(doc) {
  return doc.estado === 'facturada' && getSunatStatus(doc)?.kind === 'ok';
}

export default function BajasPage() {
  const toast = useToast();
  const [facturas, setFacturas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({ desde: '', hasta: '', estado: 'all', tipo: 'all' });
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState('all');
  const [total, setTotal] = useState(0);
  const [serverCounts, setServerCounts] = useState({ all: 0, emitida: 0, anulada: 0 });

  const [selected, setSelected] = useState(null);
  const [motivo, setMotivo] = useState('ERROR_EN_EL_RUC');
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const load = async ({ signal } = {}) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * PER_PAGE),
        limit: String(PER_PAGE),
      });
      const q = search.trim();
      if (q) params.set('q', q);
      if (activeTab === 'emitida') params.set('tab', 'emitted');
      else if (activeTab === 'anulada') params.set('tab', 'voided');
      else params.set('tab', 'all');
      if (filters.estado !== 'all') params.set('estado', filters.estado);
      if (filters.tipo !== 'all') params.set('tipo_comprobante', filters.tipo);
      if (filters.desde) params.set('desde', filters.desde);
      if (filters.hasta) params.set('hasta', filters.hasta);
      const res = await api.get(`/facturas-emitidas/page?${params.toString()}`, { signal });
      const items = Array.isArray(res) ? res : res.items || [];
      setFacturas(items);
      setTotal(Array.isArray(res) ? items.length : Number(res.total || 0));
      setServerCounts({
        all: Number(res?.counts?.all || 0),
        emitida: Number(res?.counts?.emitted || 0),
        anulada: Number(res?.counts?.voided || 0),
      });
    } catch (err) {
      if (err?.isCanceled) return;
      toast('No se pudo cargar la informacion. Revisa tu conexion e intentalo nuevamente.', 'error');
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
  }, [page, search, filters.desde, filters.hasta, filters.estado, filters.tipo, activeTab]);

  useEffect(() => {
    setPage(1);
  }, [search, filters, activeTab]);

  const setFilter = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }));

  const clearFilters = () => {
    setFilters({ desde: '', hasta: '', estado: 'all', tipo: 'all' });
    setSearch('');
  };

  const hasActiveFilters = search || filters.desde || filters.hasta || filters.estado !== 'all' || filters.tipo !== 'all';

  const tabCounts = serverCounts;
  const filtered = facturas;
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const pageItems = facturas;

  const heroCards = [
    {
      key: 'all',
      value: tabCounts.all,
      label: 'Comprobantes',
      text: `${tabCounts.all} documentos registrados`,
      link: 'Ver todos',
      icon: <FileText size={16} />,
    },
    {
      key: 'emitida',
      value: tabCounts.emitida,
      label: 'Emitidas',
      text: tabCounts.emitida ? 'Disponibles para baja' : 'Sin documentos activos',
      link: 'Ver emitidas',
      icon: <CheckCircle2 size={16} />,
    },
    {
      key: 'anulada',
      value: tabCounts.anulada,
      label: 'Anuladas',
      text: tabCounts.anulada ? 'Historico de bajas' : 'Sin anulaciones',
      link: 'Ver anuladas',
      icon: <XOctagon size={16} />,
    },
  ];

  const handleOpen = (factura) => {
    setSelected(factura);
    setMotivo('ERROR_EN_EL_RUC');
    setModalOpen(true);
  };

  const handleConfirmClick = (e) => {
    e.preventDefault();
    setModalOpen(false);
    setConfirmOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await api.post('/bajas/anular', { comprobante_id: selected.id, motivo });
      toast(`${selected.serie}-${String(selected.correlativo).padStart(6, '0')} enviado para baja`, 'success');
      setConfirmOpen(false);
      setSelected(null);
      load();
    } catch (err) {
      toast(err?.message || 'No se pudo procesar la baja. Revisa los datos e intentalo nuevamente.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-shell page-shell--dense bajas-page">
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
        </div>
      </div>

      <section className="attention document-list-hero ink-enter-2">
        <div className="attention-title document-list-hero-title">
          <div className="document-list-hero-head">
            <div className="attention-title-badge">
              <XCircle size={15} />
            </div>
          </div>

          <div className="document-list-hero-pagecopy">
            <h2>Comunicacion de Bajas</h2>
            <p>Anulacion de comprobantes emitidos ante SUNAT mediante comunicacion de baja.</p>
          </div>

          <div className="document-list-hero-kicker">
            Flujo asincrono · {tabCounts.emitida ? `${tabCounts.emitida} disponibles para baja` : 'Sin bajas pendientes'}
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
              placeholder="Buscar por serie, numero o cliente..."
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
            <span>Tipo</span>
            <CustomSelect compact value={filters.tipo} onChange={(v) => setFilter('tipo', v)} options={TIPO_FILTER_OPTS} />
          </div>
          <div className="document-list-filter">
            <span>Estado</span>
            <CustomSelect compact value={filters.estado} onChange={(v) => setFilter('estado', v)} options={STATUS_OPTIONS} />
          </div>
          <div className="document-list-filter">
            <span>Desde</span>
            <DatePicker compact value={filters.desde} onChange={(v) => setFilter('desde', v)} />
          </div>
          <div className="document-list-filter">
            <span>Hasta</span>
            <DatePicker compact value={filters.hasta} onChange={(v) => setFilter('hasta', v)} />
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
            Mostrando <strong>{getVisibleRange(page, PER_PAGE, total)}</strong> de <strong>{total}</strong>
          </div>
        </div>

        {loading ? (
          <div className="document-list-loading">
            <Spinner size="lg" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="document-list-empty">
            <EmptyState
              icon={<XCircle size={22} />}
              title={
                hasActiveFilters
                  ? 'Sin resultados para estos filtros'
                  : activeTab === 'anulada'
                    ? 'No hay comprobantes anulados en esta vista.'
                    : 'Sin comprobantes disponibles'
              }
              description={
                hasActiveFilters
                  ? 'Ajusta tipo, estado o fechas para recuperar resultados.'
                  : activeTab === 'emitida'
                    ? 'No hay comprobantes emitidos disponibles para baja.'
                    : activeTab === 'anulada'
                      ? 'Cuando se anulen documentos apareceran aqui.'
                      : 'Solo los comprobantes en estado "Emitida" pueden ser dados de baja ante SUNAT.'
              }
              action={
                hasActiveFilters ? (
                  <button className="btn-secondary" onClick={clearFilters}>
                    Limpiar filtros
                  </button>
                ) : null
              }
            />
          </div>
        ) : (
          <div className="ink-table-card document-list-table">
            <div className="ink-table-header">
              <div className="ink-table-title">
                <strong>Comprobantes</strong>
                <span>{total} visibles · {tabCounts.emitida} disponibles para baja</span>
              </div>

              <div className="document-list-table-meta">
                <span className="document-list-table-pill">
                  <CheckCircle2 size={13} />
                  {tabCounts.emitida} emitidas
                </span>
                <span className="document-list-table-pill">
                  <XOctagon size={13} />
                  {tabCounts.anulada} anuladas
                </span>
              </div>
            </div>

            <div className="ink-table-scroll">
              <table className="ink-table">
                <thead>
                  <tr>
                    <th>Numero</th>
                    <th>Tipo</th>
                    <th>Cliente</th>
                    <th>Total</th>
                    <th>Fecha emision</th>
                    <th>Estado</th>
                    <th>Accion</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((doc) => {
                    const num = `${doc.serie}-${String(doc.correlativo).padStart(6, '0')}`;
                    const clienteName = doc.cliente?.razon_social || doc.cliente?.nombre || '-';
                    const clienteDoc = doc.cliente?.numero_documento || doc.cliente?.ruc || doc.cliente?.dni;
                    const isAnulada = doc.estado === 'anulada';
                    const sunat = getSunatStatus(doc);
                    const canVoid = canVoidDocument(doc);
                    const rowClass = canVoid ? 'ink-table-row--accepted' : '';

                    return (
                      <tr key={doc.id} className={rowClass}>
                        <td data-label="Numero">
                          <div className="ink-table-cell__primary document-list-folio">{num}</div>
                          <div className="ink-table-cell__meta">
                            {doc.internal_order_number || `#${doc.id}`}
                          </div>
                        </td>
                        <td data-label="Tipo">
                          <DocumentTypeBadge tipo={doc.tipo_comprobante} size="sm" />
                        </td>
                        <td data-label="Cliente">
                          <div className="ink-table-cell__primary">{clienteName}</div>
                          {clienteDoc && <div className="ink-table-cell__meta">{clienteDoc}</div>}
                        </td>
                        <td data-label="Total">
                          <div className="ink-table-cell__primary" style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                            {formatCurrency(doc.total_venta, doc.moneda)}
                          </div>
                        </td>
                        <td data-label="Fecha emision">
                          <div className="ink-table-cell__primary">
                            {doc.fecha_emision ? new Date(doc.fecha_emision).toLocaleDateString('es-PE') : '-'}
                          </div>
                        </td>
                        <td data-label="Estado">
                          {isAnulada ? (
                            <Badge variant="error">Anulada</Badge>
                          ) : sunat?.kind === 'ok' ? (
                            <Badge variant="success">Aceptada</Badge>
                          ) : sunat?.kind === 'error' ? (
                            <Badge variant="error">Rechazada</Badge>
                          ) : (
                            <Badge variant="warning">Pendiente</Badge>
                          )}
                        </td>
                        <td data-label="Accion">
                          <div className="ink-table-row-actions document-list-row-actions">
                            {canVoid && (
                              <button
                                type="button"
                                className="ink-row-action-pill"
                                style={{ color: 'var(--color-error)' }}
                                title="Dar de baja"
                                onClick={() => handleOpen(doc)}
                              >
                                <XCircle size={14} />
                                Baja
                              </button>
                            )}
                            {!isAnulada && !canVoid && (
                              <span className="ink-table-cell__meta">No aceptado</span>
                            )}
                          </div>
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
        title="Comunicacion de baja"
        subtitle="Solicita la anulacion del comprobante desde un panel lateral sin romper la continuidad del listado."
        icon={<XCircle size={22} />}
        footer={(
          <>
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" form="baja-form" className="btn-primary" style={{ background: 'var(--color-error)' }}>
              <XCircle size={14} />
              Confirmar baja
            </button>
          </>
        )}
      >
        <form id="baja-form" onSubmit={handleConfirmClick} className="drawer-editor-form">
          <div className="drawer-editor-callout drawer-editor-callout--warning">
            <XCircle size={18} />
            <div>
              <strong>{selected && `${selected.serie}-${String(selected.correlativo).padStart(6, '0')}`}</strong>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                {selected && `${selected.cliente?.nombre || selected.cliente?.razon_social || ''} · ${formatCurrency(selected.total_venta, selected.moneda)}`}
              </p>
              <small>Esta accion notificara a SUNAT que el documento debe ser anulado. Es irreversible.</small>
            </div>
          </div>

          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header">
              <p>Motivo de la baja</p>
            </div>
            <p className="drawer-editor-section-intro">
              Selecciona la razon operativa que se reportara junto con la solicitud de anulacion.
            </p>
            <div>
              <label className="label">Motivo de la baja <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <CustomSelect value={motivo} onChange={setMotivo} options={MOTIVO_OPTS} />
            </div>
          </div>
        </form>
      </Drawer>

      <ConfirmEmitDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleSubmit}
        loading={submitting}
        mode="void"
        tipo={selected?.tipo_comprobante || '01'}
        serie={selected ? `${selected.serie}-${String(selected.correlativo).padStart(6, '0')}` : '—'}
        cliente={selected?.cliente?.nombre || selected?.cliente?.razon_social || '—'}
        total={selected?.total_venta || 0}
        moneda={selected?.moneda || 'PEN'}
        extraLines={[
          `Motivo: ${MOTIVO_OPTS.find((m) => m.value === motivo)?.label || '—'}`,
          'Esta accion es irreversible.',
        ]}
      />
    </div>
  );
}
