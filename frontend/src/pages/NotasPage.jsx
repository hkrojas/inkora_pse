import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { PageError } from '../components/ui/PageState';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { FieldError } from '../components/ui/FieldError';
import ConfirmEmitDialog from '../components/documents/ConfirmEmitDialog';
import { DocumentTypeBadge } from '../components/documents/DocumentType';
import { getSunatStatus, formatCurrency, MOTIVOS_NC, MOTIVOS_ND } from '../lib/utils/documents';
import { inventory } from '../services/inventory';

const TIPO_NOTA_OPTS = [
  { value: 'credito', label: 'Nota de crédito (07)' },
  { value: 'debito', label: 'Nota de débito (08)' },
];

const TIPO_FILTER_OPTS = [
  { value: 'all', label: 'Todas' },
  { value: 'nc', label: 'Notas de crédito (07)' },
  { value: 'nd', label: 'Notas de débito (08)' },
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'aceptado', label: 'Aceptado' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'error', label: 'Error SUNAT' },
  { value: 'anulado', label: 'Anulado' },
];

const PER_PAGE = 15;

const TAB_DEFS = [
  { key: 'all', label: 'Todas' },
  { key: 'emitted', label: 'Emitidas' },
  { key: 'pending', label: 'Pendientes' },
  { key: 'rejected', label: 'Rechazadas' },
  { key: 'voided', label: 'Anuladas' },
];

const EMPTY_FORM = {
  comprobante_afectado_id: '',
  tipo_nota: 'credito',
  cod_motivo: '',
  descripcion_motivo: '',
  inventory_impact: 'none',
  inventory_return_warehouse_id: '',
};

function getTabKey(doc) {
  const status = String(doc?.estado || '').toLowerCase();
  const sunat = getSunatStatus(doc);
  if (status === 'borrador') return 'pending';
  if (status === 'anulada' || sunat?.kind === 'voided') return 'voided';
  if (sunat?.kind === 'error') return 'rejected';
  if (sunat?.kind === 'pending') return 'pending';
  if (status === 'facturada' || sunat?.kind === 'ok') return 'emitted';
  return 'all';
}

function getNotaKind(doc) {
  return doc.document_kind === 'credit_note' ? 'nc' : 'nd';
}

function getVisibleRange(page, pageSize, total) {
  if (!total) return '0';
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return `${start}-${end}`;
}

function getAffectedDocument(doc) {
  return doc?.nota_referencia || doc?.source_quote || null;
}

function formatDocumentRef(doc) {
  if (!doc) return '';
  if (doc.document_number) return doc.document_number;
  return `${doc.serie || ''}-${String(doc.correlativo || '').padStart(6, '0')}`;
}

export default function NotasPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [notas, setNotas] = useState([]);
  const [facturas, setFacturas] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [backendCounts, setBackendCounts] = useState({ all: 0, emitted: 0, pending: 0, rejected: 0, voided: 0 });
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({ desde: '', hasta: '', estado: 'all', tipo: 'all' });
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState('all');

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [formErrors, setFormErrors] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * PER_PAGE),
        limit: String(PER_PAGE),
        tab: activeTab,
      });
      if (filters.tipo !== 'all') params.set('tipo_nota', filters.tipo);
      if (filters.estado !== 'all') params.set('estado', filters.estado);
      if (filters.desde) params.set('desde', filters.desde);
      if (filters.hasta) params.set('hasta', filters.hasta);
      if (search.trim()) params.set('q', search.trim());
      const [notasRes, facturasRes, warehousesRes] = await Promise.all([
        api.get(`/notas/page?${params.toString()}`),
        api.get('/facturas-emitidas/page?limit=15&tab=emitted'),
        inventory.warehouses().catch(() => []),
      ]);
      const notaItems = Array.isArray(notasRes) ? notasRes : notasRes.items || [];
      const facturaItems = Array.isArray(facturasRes) ? facturasRes : facturasRes.items || [];
      setNotas(notaItems);
      setTotal(Array.isArray(notasRes) ? notaItems.length : notasRes.total || 0);
      setBackendCounts(notasRes.counts || { all: notaItems.length, emitted: 0, pending: 0, rejected: 0, voided: 0 });
      setFacturas(facturaItems.filter((f) => f.estado === 'facturada' || f.sunat_accepted));
      setWarehouses(warehousesRes || []);
    } catch (err) {
      setNotas([]);
      setTotal(0);
      setBackendCounts({ all: 0, emitted: 0, pending: 0, rejected: 0, voided: 0 });
      setError(err);
      toast(err.message || 'No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error');
    } finally {
      setLoading(false);
    }
  }, [activeTab, filters.desde, filters.estado, filters.hasta, filters.tipo, page, search, toast]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    setPage(1);
  }, [search, filters, activeTab]);

  const setFilter = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }));

  const clearFilters = () => {
    setFilters({ desde: '', hasta: '', estado: 'all', tipo: 'all' });
    setSearch('');
  };

  const hasActiveFilters = search || filters.desde || filters.hasta || filters.estado !== 'all' || filters.tipo !== 'all';
  const pristineEmpty = !loading && !error && backendCounts.all === 0 && !hasActiveFilters && activeTab === 'all';

  const constrained = useMemo(
    () =>
      notas.filter((doc) => {
        const q = search.trim().toLowerCase();
        const sunat = getSunatStatus(doc);
        const cliente = doc.cliente?.razon_social || doc.cliente?.nombre || '';
        const num = `${doc.serie || ''}-${String(doc.correlativo || '').padStart(6, '0')}`;
        const afectado = formatDocumentRef(getAffectedDocument(doc));
        const matchSearch =
          !q ||
          cliente.toLowerCase().includes(q) ||
          (doc.cliente?.numero_documento || '').includes(q) ||
          num.toLowerCase().includes(q) ||
          afectado.toLowerCase().includes(q) ||
          (doc.nota_motivo_descripcion || '').toLowerCase().includes(q);
        const matchDesde = !filters.desde || new Date(doc.fecha_emision) >= new Date(filters.desde);
        const matchHasta = !filters.hasta || new Date(doc.fecha_emision) <= new Date(filters.hasta);
        const matchEstado =
          filters.estado === 'all' ||
          (filters.estado === 'aceptado' && sunat?.kind === 'ok') ||
          (filters.estado === 'pendiente' && sunat?.kind === 'pending') ||
          (filters.estado === 'error' && sunat?.kind === 'error') ||
          (filters.estado === 'anulado' && (sunat?.kind === 'voided' || doc.estado === 'anulada'));
        const matchTipo =
          filters.tipo === 'all' ||
          (filters.tipo === 'nc' && doc.document_kind === 'credit_note') ||
          (filters.tipo === 'nd' && doc.document_kind === 'debit_note');
        return matchSearch && matchDesde && matchHasta && matchEstado && matchTipo;
      }),
    [notas, search, filters],
  );

  const tabCounts = backendCounts;

  const filtered = useMemo(
    () => constrained.filter((doc) => activeTab === 'all' || getTabKey(doc) === activeTab),
    [constrained, activeTab],
  );

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const pageItems = filtered;

  const metrics = useMemo(() => {
    const accepted = constrained.filter((doc) => getSunatStatus(doc)?.kind === 'ok').length;
    const pending = constrained.filter((doc) => getSunatStatus(doc)?.kind === 'pending').length;
    const rejected = constrained.filter((doc) => getSunatStatus(doc)?.kind === 'error').length;
    const nc = constrained.filter((doc) => doc.document_kind === 'credit_note').length;
    const nd = constrained.filter((doc) => doc.document_kind === 'debit_note').length;
    return { accepted, pending, rejected, nc, nd };
  }, [constrained]);

  const visibleMetrics = useMemo(() => {
    const accepted = filtered.filter((doc) => getSunatStatus(doc)?.kind === 'ok').length;
    const pending = filtered.filter((doc) => getSunatStatus(doc)?.kind === 'pending').length;
    const rejected = filtered.filter((doc) => getSunatStatus(doc)?.kind === 'error').length;
    return { accepted, pending, rejected };
  }, [filtered]);

  const acceptedRate = constrained.length
    ? Math.round((metrics.accepted / constrained.length) * 100)
    : 0;

  const heroCards = [
    {
      key: 'all',
      value: constrained.length,
      label: 'Notas visibles',
      text: `${metrics.nc} NC · ${metrics.nd} ND registradas`,
      link: 'Ver todas',
      icon: <FileText size={16} />,
    },
    {
      key: 'emitted',
      value: metrics.accepted,
      label: 'Aceptadas SUNAT',
      text: `${acceptedRate}% del total actual`,
      link: 'Abrir emitidas',
      icon: <CheckCircle2 size={16} />,
    },
    {
      key: 'pending',
      value: metrics.pending,
      label: 'Pendientes',
      text: metrics.pending ? 'Requieren seguimiento o recarga' : 'Sin espera pendiente',
      link: 'Revisar pendientes',
      icon: <Clock3 size={16} />,
    },
    {
      key: 'rejected',
      value: metrics.rejected,
      label: 'Observadas',
      text: metrics.rejected ? 'Necesitan correccion o reenvio' : 'Sin errores SUNAT',
      link: 'Ver observadas',
      icon: <XOctagon size={16} />,
    },
  ];

  const motivosOpts = form.tipo_nota === 'credito' ? MOTIVOS_NC : MOTIVOS_ND;

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
    if (!form.descripcion_motivo.trim()) errs.descripcion = 'La descripcion del motivo es obligatoria';
    if (form.inventory_impact === 'physical_return' && !form.inventory_return_warehouse_id) {
      errs.warehouse = 'Seleccione el almacén que recibirá la devolución';
    }
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
        inventory_impact: form.tipo_nota === 'credito' ? form.inventory_impact : 'none',
        inventory_return_warehouse_id: form.inventory_impact === 'physical_return'
          ? Number(form.inventory_return_warehouse_id)
          : null,
      });
      toast('Nota emitida correctamente', 'success');
      setConfirmOpen(false);
      setModalOpen(false);
      setForm(EMPTY_FORM);
      setFormErrors({});
      load();
    } catch (err) {
      toast(err?.message || 'No se pudo emitir la nota. Revisa los datos e intentalo nuevamente.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const openModal = () => {
    navigate('/notas/nueva');
  };

  const tipoNotaBadge = form.tipo_nota === 'credito' ? '07' : '08';

  return (
    <div className="page-shell page-shell--dense notas-page">
      <div className="page-head ink-enter-1">
        <div className="page-actions document-list-page-actions">
          <button
            type="button"
            className="btn"
            onClick={() => toast('La exportación está en desarrollo.', 'info')}
          >
            <Download size={15} />
            Exportar
          </button>

          <button className="btn-primary" onClick={openModal}>
            <Plus size={15} />
            Nueva nota
          </button>
        </div>
      </div>

      <section className="attention document-list-hero ink-enter-2">
        <div className="attention-title document-list-hero-title">
          <div className="document-list-hero-head">
            <div className="attention-title-badge">
              <FileText size={15} />
            </div>
          </div>

          <div className="document-list-hero-pagecopy">
            <h2>Notas de crédito / débito</h2>
            <p>Ajustes sobre comprobantes emitidos, aceptados ante SUNAT.</p>
          </div>

          <div className="document-list-hero-kicker">
            Tipos 07 y 08 · {tabCounts.pending ? `${tabCounts.pending} por revisar` : 'Operación estable'}
          </div>
        </div>

        {!pristineEmpty && heroCards.map((item) => (
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
        {!pristineEmpty && <>
        <div className="toolbar">
          <label className="search-box">
            <Search size={16} />
            <input
              placeholder="Buscar por serie, comprobante afectado o cliente..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>

          <div className="toolbar-actions">
            {metrics.pending > 0 && (
              <button type="button" className="btn-secondary" onClick={load}>
                <RefreshCw size={15} />
                Actualizar estados
              </button>
            )}
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
            <span>Tipo de nota</span>
            <CustomSelect compact value={filters.tipo} onChange={(v) => setFilter('tipo', v)} options={TIPO_FILTER_OPTS} />
          </div>
          <div className="document-list-filter">
            <span>Estado SUNAT</span>
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
        </>}

        {error ? (
          <div className="document-list-empty">
            <PageError error={error} onRetry={load} />
          </div>
        ) : loading ? (
          <div className="document-list-loading">
            <Spinner size="lg" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="document-list-empty">
            <EmptyState
              variant={pristineEmpty ? 'onboarding' : 'default'}
              icon={<FileText size={22} />}
              title={
                hasActiveFilters
                  ? 'Sin resultados para estos filtros'
                  : activeTab === 'all'
                    ? 'Aún no tienes notas emitidas'
                    : activeTab === 'emitted'
                      ? 'No hay notas aceptadas en esta vista.'
                      : activeTab === 'pending'
                        ? 'No hay notas pendientes de respuesta SUNAT.'
                        : activeTab === 'rejected'
                          ? 'No hay notas rechazadas u observadas.'
                          : 'No hay notas anuladas en esta vista.'
              }
              description={
                hasActiveFilters
                  ? 'Ajusta tipo, fechas o estado para recuperar resultados de esta vista.'
                  : activeTab === 'all'
                    ? 'Emite tu primera nota de crédito o débito para corregir o ajustar un comprobante ya aceptado por SUNAT.'
                    : 'Cuando existan documentos en este estado aparecerán aquí con sus acciones recomendadas.'
              }
              action={
                hasActiveFilters ? (
                  <button className="btn-secondary" onClick={clearFilters}>
                    Limpiar filtros
                  </button>
                ) : (
                  <button className="btn-primary" onClick={openModal}>
                    <Plus size={15} />
                    Nueva nota
                  </button>
                )
              }
            />
          </div>
        ) : (
          <div className="ink-table-card document-list-table">
            <div className="ink-table-header">
              <div className="ink-table-title">
                <strong>Notas de crédito / débito</strong>
                <span>
                  {filtered.length} visibles · {metrics.nc} NC · {metrics.nd} ND
                </span>
              </div>

              <div className="document-list-table-meta">
                <span className="document-list-table-pill">
                  <CheckCircle2 size={13} />
                  {visibleMetrics.accepted} aceptadas
                </span>
                <span className="document-list-table-pill">
                  <Clock3 size={13} />
                  {visibleMetrics.pending} pendientes
                </span>
                <span className="document-list-table-pill">
                  <XOctagon size={13} />
                  {visibleMetrics.rejected} observadas
                </span>
              </div>
            </div>

            <div className="ink-table-scroll">
              <table className="ink-table ink-note-table">
                <thead>
                  <tr>
                    <th>Numero</th>
                    <th>Tipo</th>
                    <th>Comprobante afectado</th>
                    <th>Cliente</th>
                    <th>Motivo</th>
                    <th>Estado SUNAT</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((doc) => {
                    const sunat = getSunatStatus(doc);
                    const num = doc.estado === 'borrador'
                      ? 'Sin correlativo'
                      : `${doc.serie}-${String(doc.correlativo).padStart(6, '0')}`;
                    const clienteName = doc.cliente?.razon_social || doc.cliente?.nombre || '-';
                    const clienteDoc = doc.cliente?.numero_documento || doc.cliente?.ruc || doc.cliente?.dni;
                    const affectedDoc = getAffectedDocument(doc);
                    const afectado = formatDocumentRef(affectedDoc) || '—';
                    const rowClass =
                      sunat?.kind === 'ok'
                        ? 'ink-table-row--accepted'
                        : sunat?.kind === 'pending'
                          ? 'ink-table-row--active'
                          : '';

                    return (
                      <tr key={doc.id} className={rowClass}>
                        <td data-label="Numero">
                          <div className="ink-table-cell__primary document-list-folio">{num}</div>
                          <div className="ink-table-cell__meta">
                            {doc.fecha_emision ? new Date(doc.fecha_emision).toLocaleDateString('es-PE') : ''}
                          </div>
                        </td>
                        <td data-label="Tipo">
                          <DocumentTypeBadge tipo={doc.document_kind === 'credit_note' ? '07' : '08'} size="sm" />
                        </td>
                        <td data-label="Comprobante afectado">
                          <div className="ink-table-cell__primary">{afectado}</div>
                          {affectedDoc?.tipo_comprobante && (
                            <div className="ink-table-cell__meta">
                              <DocumentTypeBadge tipo={affectedDoc.tipo_comprobante} size="sm" />
                            </div>
                          )}
                        </td>
                        <td data-label="Cliente">
                          <div className="ink-table-cell__primary">{clienteName}</div>
                          {clienteDoc && <div className="ink-table-cell__meta">{clienteDoc}</div>}
                        </td>
                        <td data-label="Motivo">
                          <div className="ink-table-cell__primary" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {doc.nota_motivo_descripcion || '—'}
                          </div>
                        </td>
                        <td data-label="Estado SUNAT">
                          {sunat ? (
                            <Badge variant={sunat.variant === 'danger' ? 'error' : sunat.variant} title={sunat.tooltip}>
                              {sunat.label}
                            </Badge>
                          ) : (
                            <Badge variant="default">Sin estado</Badge>
                          )}
                        </td>
                        <td data-label="Acciones">
                          <div className="ink-table-row-actions document-list-row-actions">
                            {doc.estado === 'borrador' && (
                              <button type="button" className="ink-row-btn" title="Continuar borrador" onClick={() => navigate(`/notas/nueva?draft=${doc.id}`)}>
                                <ArrowRight size={14} />
                              </button>
                            )}
                            {sunat?.kind === 'pending' && (
                              <button type="button" className="ink-row-btn" title="Recargar estado SUNAT" onClick={load}>
                                <RefreshCw size={14} />
                              </button>
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
        title="Nueva nota de crédito / débito"
        subtitle="Ajuste fiscal sobre comprobante aceptado"
        icon={<FileText size={18} />}
      >
        <div className="space-y-4">
          <div>
            <label className="label">Tipo de nota</label>
            <CustomSelect
              value={form.tipo_nota}
              onChange={(v) => setForm((c) => ({ ...c, tipo_nota: v, cod_motivo: '' }))}
              options={TIPO_NOTA_OPTS}
            />
          </div>

          <div>
            <label className="label">
              Comprobante afectado <span style={{ color: 'var(--color-error)' }}>*</span>
            </label>
            <CustomSelect
              value={form.comprobante_afectado_id}
              onChange={(v) => { setForm((c) => ({ ...c, comprobante_afectado_id: v })); setFormErrors((e) => ({ ...e, comprobante: undefined })); }}
              options={facturasOpts}
              searchable
              searchPlaceholder="Buscar por numero o cliente..."
              placeholder="Seleccionar factura o boleta..."
              filterOption={(opt, q) => opt.searchText?.toLowerCase().includes(q)}
              renderOption={(opt) => (
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', minWidth: 0 }}>
                  <div style={{ minWidth: 0 }}>
                    <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, color: 'var(--brand-600)' }}>{opt.num}</p>
                    <p style={{ fontSize: '12px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{opt.cliente}</p>
                    <p style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>{opt.fecha}</p>
                  </div>
                  <p style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', flexShrink: 0 }}>{opt.total}</p>
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
              <div style={{ marginTop: '6px', padding: '8px 12px', background: 'var(--bg-surface-2)', border: '1px solid var(--border-rule)', fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', gap: '16px' }}>
                <span><strong style={{ color: 'var(--text-primary)' }}>{selectedFactura.num}</strong></span>
                <span>{selectedFactura.cliente}</span>
                <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>{selectedFactura.total}</span>
              </div>
            )}
          </div>

          <div>
            <label className="label">Motivo <span style={{ color: 'var(--color-error)' }}>*</span></label>
            <CustomSelect
              value={form.cod_motivo}
              onChange={(v) => { setForm((c) => ({ ...c, cod_motivo: v })); setFormErrors((e) => ({ ...e, motivo: undefined })); }}
              options={motivosOpts}
              placeholder="Seleccionar motivo..."
            />
            <FieldError message={formErrors.motivo} />
          </div>

          <div>
            <label className="label">Descripcion del motivo <span style={{ color: 'var(--color-error)' }}>*</span></label>
            <input
              className="input"
              value={form.descripcion_motivo}
              onChange={(e) => { setForm((c) => ({ ...c, descripcion_motivo: e.target.value })); setFormErrors((e2) => ({ ...e2, descripcion: undefined })); }}
              placeholder="Ej: Devolucion de mercaderia por defecto"
            />
            <FieldError message={formErrors.descripcion} />
          </div>

          {form.tipo_nota === 'credito' && (
            <div>
              <label className="label">Impacto en inventario</label>
              <select
                className="input"
                value={form.inventory_impact}
                onChange={(event) => setForm((current) => ({ ...current, inventory_impact: event.target.value }))}
              >
                <option value="none">Sin movimiento · corrección de precio o datos</option>
                <option value="undelivered">Cantidad no entregada · reponer al aceptar SUNAT</option>
                <option value="physical_return">Devolución física · ingresar al confirmar recepción</option>
              </select>
              <p className="mt-1 text-xs text-[var(--color-text-muted)]">La nota fiscal y la recepción física quedan trazadas por separado.</p>
            </div>
          )}

          {form.tipo_nota === 'credito' && form.inventory_impact === 'physical_return' && (
            <div>
              <label className="label">Almacén receptor</label>
              <select
                className="input"
                value={form.inventory_return_warehouse_id}
                onChange={(event) => setForm((current) => ({ ...current, inventory_return_warehouse_id: event.target.value }))}
              >
                <option value="">Seleccionar almacén...</option>
                {warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>)}
              </select>
              <FieldError message={formErrors.warehouse} />
            </div>
          )}

          <div className="responsive-form-actions">
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="button" className="btn-primary" onClick={handleEmitClick}>
              Revisar y emitir nota
            </button>
          </div>
        </div>
      </Drawer>

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
