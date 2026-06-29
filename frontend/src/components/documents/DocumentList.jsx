import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Download,
  Eye,
  ExternalLink,
  FileArchive,
  FileText,
  Mail,
  MessageCircle,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Send,
  Search,
  Share2,
  XCircle,
  XOctagon,
} from 'lucide-react';
import { api } from '../../lib/utils/api';
import { useToast } from '../ui/Toast';
import Spinner from '../ui/Spinner';
import Badge from '../ui/Badge';
import CustomSelect from '../ui/CustomSelect';
import DatePicker from '../ui/DatePicker';
import { DocumentTypeBadge } from './DocumentType';
import { formatCurrency } from '../../lib/utils/documents';
import {
  buildFiscalDownloadRequest,
  canRetryFiscalArtifacts,
  formatFiscalDate,
  getFiscalArtifactStatus,
  getFiscalDocumentStatus,
  hasFiscalDownload,
} from '../../lib/utils/documentArtifacts';
import EmptyState from '../ui/EmptyState';
import { PageError } from '../ui/PageState';
import useDebouncedValue from '../../hooks/useDebouncedValue';

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'aceptado', label: 'Aceptado' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'error', label: 'Observadas' },
  { value: 'anulado', label: 'Anulado' },
];

const MONEDA_OPTIONS = [
  { value: 'all', label: 'Todas' },
  { value: 'PEN', label: 'S/ Soles' },
  { value: 'USD', label: '$ Dolares' },
];

const PER_PAGE = 15;

const TAB_DEFS = [
  { key: 'all', label: 'Todas' },
  { key: 'draft', label: 'Borradores' },
  { key: 'emitted', label: 'Emitidas' },
  { key: 'pending', label: 'Pendientes' },
  { key: 'rejected', label: 'Rechazadas' },
  { key: 'voided', label: 'Anuladas' },
];

const STATUS_TO_TAB = {
  aceptado: 'emitted',
  pendiente: 'pending',
  error: 'rejected',
  anulado: 'voided',
};

function getDocumentFamily(tipo, title) {
  if (tipo === '01') {
    return {
      pageTitle: 'Facturas',
      heroSubtitle: 'Aceptacion, archivos y seguimiento en una sola vista.',
      emptyTitle: 'Aun no tienes facturas emitidas',
      emptyDescription: 'Crea tu primera factura usando un cliente registrado o una cotizacion aprobada.',
      filteredEmptyTitle: 'No hay facturas para esta vista',
      newFallback: 'Nueva factura',
    };
  }

  if (tipo === '03') {
    return {
      pageTitle: 'Boletas',
      heroSubtitle: 'Aceptacion, archivos y seguimiento en una sola vista.',
      emptyTitle: 'Aun no tienes boletas emitidas',
      emptyDescription: 'Emite la primera boleta cuando el cliente necesite un comprobante rapido y validado.',
      filteredEmptyTitle: 'No hay boletas para esta vista',
      newFallback: 'Nueva boleta',
    };
  }

  return {
    pageTitle: title || 'Comprobantes',
    heroSubtitle: 'Documentos emitidos y listos para seguimiento.',
    emptyTitle: 'Aun no tienes comprobantes emitidos',
    emptyDescription: 'Crea tu primer comprobante usando un cliente registrado o una cotizacion aprobada.',
    filteredEmptyTitle: 'No hay comprobantes para esta vista',
    newFallback: 'Nuevo comprobante',
  };
}

function getVisibleRange(page, pageSize, total) {
  if (!total) return '0';
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return `${start}-${end}`;
}

function getStateEmptyCopy(activeTab, family) {
  if (activeTab === 'draft') return `No hay ${family.pageTitle.toLowerCase()} en borrador.`;
  if (activeTab === 'emitted') return `No hay ${family.pageTitle.toLowerCase()} aceptadas en esta vista.`;
  if (activeTab === 'pending') return `No hay ${family.pageTitle.toLowerCase()} pendientes de validacion.`;
  if (activeTab === 'rejected') return `No hay ${family.pageTitle.toLowerCase()} rechazadas u observadas.`;
  if (activeTab === 'voided') return `No hay ${family.pageTitle.toLowerCase()} anuladas en esta vista.`;
  return family.filteredEmptyTitle;
}

const PROVIDER_VERIFICATION_LABELS = {
  verified: { label: 'Validada', kind: 'verified' },
  pending: { label: 'Pendiente de validacion', kind: 'pending' },
  failed: { label: 'Validacion fallida', kind: 'failed' },
};

function getProviderVerificationMeta(status) {
  return PROVIDER_VERIFICATION_LABELS[status] || null;
}

function normalizeActionLabel(label, fallback) {
  const raw = String(label || fallback || '').trim();
  return raw.replace(/^\+\s*/, '');
}

function formatDocNumber(doc) {
  return `${doc.serie || '-'}-${String(doc.correlativo || 0).padStart(6, '0')}`;
}

function csvCell(value) {
  const text = String(value ?? '').replaceAll('"', '""');
  return `"${text}"`;
}

function downloadTextFile(filename, content, mime = 'text/csv;charset=utf-8') {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function filenameFromDisposition(disposition, fallback) {
  const match = /filename="?([^"]+)"?/i.exec(disposition || '');
  return match?.[1] || fallback;
}

function downloadBlobFile(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function getFiscalDocumentName(doc) {
  if (doc?.tipo_comprobante === '01') return 'factura';
  if (doc?.tipo_comprobante === '03') return 'boleta';
  if (doc?.tipo_comprobante === '07') return 'nota de credito';
  if (doc?.tipo_comprobante === '08') return 'nota de debito';
  return 'comprobante';
}

export default function DocumentList({ tipo, title, subtitle, newLabel, newHref, endpoint }) {
  const [docs, setDocs] = useState([]);
  const [total, setTotal] = useState(0);
  const [tabCounts, setTabCounts] = useState({ all: 0, draft: 0, emitted: 0, pending: 0, rejected: 0, voided: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);
  const [retryingArtifactsId, setRetryingArtifactsId] = useState(null);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({ desde: '', hasta: '', estado: 'all', moneda: 'all' });
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState('all');
  const [openActionMenu, setOpenActionMenu] = useState(null);
  const toast = useToast();
  const debouncedSearch = useDebouncedValue(search, 300);

  const family = useMemo(() => getDocumentFamily(tipo, title), [tipo, title]);
  const primaryLabel = useMemo(
    () => normalizeActionLabel(newLabel, family.newFallback),
    [newLabel, family.newFallback],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const selectedTab = filters.estado !== 'all'
        ? STATUS_TO_TAB[filters.estado] || 'all'
        : activeTab;
      const params = new URLSearchParams({
        skip: String((page - 1) * PER_PAGE),
        limit: String(PER_PAGE),
        tab: selectedTab,
      });
      if (tipo) params.set('tipo_comprobante', tipo);
      if (debouncedSearch.trim()) params.set('q', debouncedSearch.trim());
      if (filters.desde) params.set('desde', filters.desde);
      if (filters.hasta) params.set('hasta', filters.hasta);
      if (filters.moneda !== 'all') params.set('moneda', filters.moneda);
      const url = endpoint || `/facturas-emitidas/page?${params.toString()}`;
      const data = await api.get(url);
      const items = Array.isArray(data) ? data : data.items || [];
      setDocs(items);
      setTotal(Array.isArray(data) ? items.length : data.total || 0);
      setTabCounts(data.counts || { all: items.length, draft: 0, emitted: 0, pending: 0, rejected: 0, voided: 0 });
    } catch (err) {
      setError(err);
      setDocs([]);
      setTotal(0);
      setTabCounts({ all: 0, draft: 0, emitted: 0, pending: 0, rejected: 0, voided: 0 });
      toast(err.message || 'No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error');
    } finally {
      setLoading(false);
    }
  }, [activeTab, debouncedSearch, endpoint, filters, page, tipo, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, filters, activeTab]);

  const setFilter = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }));

  const toggleActionMenu = (key) => {
    setOpenActionMenu((current) => (current === key ? null : key));
  };

  const runActionMenuItem = (handler) => {
    setOpenActionMenu(null);
    handler();
  };

  const clearFilters = () => {
    setFilters({ desde: '', hasta: '', estado: 'all', moneda: 'all' });
    setSearch('');
  };

  const exportCurrentView = () => {
    if (!docs.length) {
      toast('No hay documentos para exportar.', 'error');
      return;
    }

    const headers = ['folio', 'fecha_emision', 'cliente', 'documento_cliente', 'tipo', 'moneda', 'total', 'estado', 'sunat'];
    const rows = docs.map((doc) => {
      const sunat = getFiscalDocumentStatus(doc);
      return [
        formatDocNumber(doc),
        doc.fecha_emision ? formatFiscalDate(doc.fecha_emision) : '',
        doc.cliente?.razon_social || doc.cliente?.nombre || '',
        doc.cliente?.numero_documento || '',
        doc.tipo_comprobante || '',
        doc.moneda || 'PEN',
        Number(doc.total_venta || 0).toFixed(2),
        doc.estado || '',
        sunat?.label || '',
      ].map(csvCell).join(',');
    });
    downloadTextFile(`${family.pageTitle.toLowerCase()}-${new Date().toISOString().slice(0, 10)}.csv`, [headers.join(','), ...rows].join('\n'));
    toast('Exportación CSV generada.', 'success');
  };

  const downloadFiscalFile = async (doc, type) => {
    setDownloadingId(`${doc.id}-${type}`);
    try {
      const fallback = `${formatDocNumber(doc)}.${type === 'cdr' ? 'zip' : type}`;
      const target = buildFiscalDownloadRequest(doc, type);
      if (target.method === 'get') {
        const data = await api.get(target.path, { timeoutMs: 45000 });
        if (data?.url) {
          window.open(data.url, '_blank', 'noopener,noreferrer');
          return;
        }
        throw new Error('No se pudo preparar la descarga del PDF.');
      }
      const { blob, disposition } = await api.blob(target.path, target.body, { timeoutMs: 45000 });
      downloadBlobFile(blob, filenameFromDisposition(disposition, fallback));
    } catch (err) {
      toast(err.message || 'No se pudo descargar el archivo fiscal.', 'error');
    } finally {
      setDownloadingId(null);
    }
  };

  const resolveSharePayload = async (doc) => {
    try {
      return await api.get(`/cotizaciones/${doc.id}/compartir`);
    } catch (err) {
      toast(err.message || 'No se pudo preparar el enlace para compartir.', 'error');
      return null;
    }
  };

  const handleOpenFiscalPdf = async (doc) => {
    try {
      const data = await api.get(`/cotizaciones/${doc.id}/pdf`, { timeoutMs: 45000 });
      const url = data?.url || data?.url_compartir || data?.public_url || doc.sunat_pdf_url;
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
        return;
      }
      toast('No se pudo abrir el PDF del comprobante.', 'error');
    } catch (err) {
      toast(err.message || 'No se pudo abrir el PDF del comprobante.', 'error');
    }
  };

  const handleRetryArtifacts = async (doc) => {
    setRetryingArtifactsId(doc.id);
    try {
      await api.post(`/facturacion/${doc.id}/artifacts/retry`, {}, { timeoutMs: 60000 });
      toast('Artefactos fiscales reconstruidos.', 'success');
      await load();
    } catch (err) {
      toast(err.message || 'No se pudieron reconstruir los artefactos fiscales.', 'error');
    } finally {
      setRetryingArtifactsId(null);
    }
  };

  const handleCopyShareLink = async (doc) => {
    const data = await resolveSharePayload(doc);
    const url = data?.url_compartir || data?.url || data?.public_url;
    if (!url) {
      toast('No se pudo generar el enlace publico.', 'error');
      return;
    }

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        window.prompt('Copia el enlace:', url);
      }
      toast('Enlace publico copiado.', 'success');
    } catch {
      window.prompt('Copia el enlace:', url);
    }
  };

  const openShareLink = (link, channel) => {
    if (!link) {
      toast(
        channel === 'email'
          ? 'El cliente no tiene correo registrado.'
          : 'El cliente no tiene WhatsApp valido.',
        'error',
      );
      return false;
    }

    if (channel === 'email') {
      window.location.href = link;
    } else {
      window.open(link, '_blank', 'noopener,noreferrer');
    }
    return true;
  };

  const handleOpenShareChannel = async (doc, channel) => {
    const data = await resolveSharePayload(doc);
    if (!data) return;
    openShareLink(channel === 'email' ? data.mailto_link : data.whatsapp_link, channel);
  };

  const handleOpenCombinedShare = async (doc) => {
    const data = await resolveSharePayload(doc);
    if (!data) return;
    const openedWhatsApp = openShareLink(data.whatsapp_link, 'whatsapp');
    if (data.mailto_link) {
      window.setTimeout(() => openShareLink(data.mailto_link, 'email'), openedWhatsApp ? 120 : 0);
    } else {
      toast('El cliente no tiene correo registrado.', 'error');
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const pageItems = docs;

  const hasActiveFilters =
    search || filters.desde || filters.hasta || filters.estado !== 'all' || filters.moneda !== 'all';

  const metrics = useMemo(() => {
    const accepted = tabCounts.emitted || 0;
    const pending = tabCounts.pending || 0;
    const rejected = tabCounts.rejected || 0;
    const amount = docs.reduce((sum, doc) => sum + Number(doc.total_venta || 0), 0);
    return { accepted, pending, rejected, amount };
  }, [docs, tabCounts]);

  const visibleMetrics = useMemo(() => {
    const accepted = docs.filter((doc) => getFiscalDocumentStatus(doc)?.kind === 'ok').length;
    const pending = docs.filter((doc) => getFiscalDocumentStatus(doc)?.kind === 'pending').length;
    const rejected = docs.filter((doc) => getFiscalDocumentStatus(doc)?.kind === 'error').length;
    const amount = docs.reduce((sum, doc) => sum + Number(doc.total_venta || 0), 0);
    return { accepted, pending, rejected, amount };
  }, [docs]);

  const acceptedRate = tabCounts.all
    ? Math.round((metrics.accepted / tabCounts.all) * 100)
    : 0;

  const heroCards = [
    {
      key: 'all',
      value: tabCounts.all || total,
      label: `${family.pageTitle} visibles`,
      text: formatCurrency(metrics.amount, 'PEN'),
      link: 'Ver todas',
      icon: <FileText size={16} />,
    },
    {
      key: 'emitted',
      value: metrics.accepted,
      label: 'Aceptadas',
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
      text: metrics.rejected ? 'Necesitan correccion' : 'Sin observaciones',
      link: 'Ver observadas',
      icon: <XOctagon size={16} />,
    },
  ];

  return (
    <div className="page-shell page-shell--dense">
      <div className="page-head ink-enter-1">
        <div className="page-actions document-list-page-actions">
          <button
            type="button"
            className="btn"
            onClick={exportCurrentView}
          >
            <Download size={15} />
            Exportar
          </button>

          {newHref && (
            <Link className="btn-primary" to={newHref}>
              <Plus size={15} />
              {primaryLabel}
            </Link>
          )}
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
            <h2>{family.pageTitle}</h2>
            <p>
              {family.heroSubtitle || subtitle || `Administra ${family.pageTitle.toLowerCase()} emitidas, estados y acciones pendientes.`}
            </p>
          </div>

          <div className="document-list-hero-kicker">
            {tipo ? `Tipo ${tipo}` : 'Comprobantes'} · {tabCounts.pending ? `${tabCounts.pending} por revisar` : 'Operación estable'}
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
              placeholder="Buscar por serie, número o cliente..."
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
            <span>Estado</span>
            <CustomSelect compact value={filters.estado} onChange={(v) => setFilter('estado', v)} options={STATUS_OPTIONS} />
          </div>
          <div className="document-list-filter">
            <span>Moneda</span>
            <CustomSelect compact value={filters.moneda} onChange={(v) => setFilter('moneda', v)} options={MONEDA_OPTIONS} />
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

        {error && !loading ? (
          <div className="document-list-empty">
            <PageError error={error} onRetry={load} />
          </div>
        ) : loading ? (
          <div className="document-list-loading">
            <Spinner size="lg" />
          </div>
        ) : docs.length === 0 ? (
          <div className="document-list-empty">
            <EmptyState
              icon={<FileText size={22} />}
              title={
                hasActiveFilters
                  ? 'Sin resultados para estos filtros'
                  : activeTab === 'all'
                    ? family.emptyTitle
                    : getStateEmptyCopy(activeTab, family)
              }
              description={
                hasActiveFilters
                  ? 'Ajusta fechas, moneda o estado para recuperar resultados de esta vista.'
                  : activeTab === 'all'
                    ? family.emptyDescription
                    : 'Cuando existan documentos en este estado aparecerán aquí con sus acciones recomendadas.'
              }
              action={
                hasActiveFilters ? (
                  <button className="btn-secondary" onClick={clearFilters}>
                    Limpiar filtros
                  </button>
                ) : newHref ? (
                  <Link className="btn-primary" to={newHref}>
                    <Plus size={15} />
                    {primaryLabel}
                  </Link>
                ) : null
              }
            />
          </div>
        ) : (
          <div className="ink-table-card document-list-table">
            <div className="ink-table-header">
              <div className="ink-table-title">
                <strong>{title}</strong>
                <span>
                  {total} visibles · {formatCurrency(visibleMetrics.amount, 'PEN')} en esta página
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
              <table className="ink-table ink-document-table">
                <thead>
                  <tr>
                    <th>Folio</th>
                    <th>Fecha</th>
                    <th>Cliente</th>
                    <th>Tipo</th>
                    <th className="text-right">Total</th>
                    <th>Estado</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((doc) => {
                    const sunat = getFiscalDocumentStatus(doc);
                    const num = formatDocNumber(doc);
                    const desktopMenuKey = `${doc.id}-desktop`;
                    const mobileMenuKey = `${doc.id}-mobile`;
                    const clienteName = doc.cliente?.razon_social || doc.cliente?.nombre || '-';
                    const clienteDoc = doc.cliente?.numero_documento || doc.cliente?.ruc || doc.cliente?.dni;
                    const rowClass =
                      sunat?.kind === 'ok'
                        ? 'ink-table-row--accepted'
                        : sunat?.kind === 'pending'
                          ? 'ink-table-row--active'
                          : '';
                    const pdfArtifact = getFiscalArtifactStatus(doc, 'pdf');
                    const cdrArtifact = getFiscalArtifactStatus(doc, 'cdr');
                    const canRetryArtifacts = canRetryFiscalArtifacts(doc);
                    const verificationMeta = getProviderVerificationMeta(doc.provider_verification_status);

                    return (
                      <tr key={doc.id} className={rowClass}>
                        <td data-label="Folio">
                          <div className="ink-table-cell__primary document-list-folio">{num}</div>
                          <div className="ink-table-cell__meta">
                            Serie {doc.serie || '-'} · Corr. {doc.correlativo || '-'}
                          </div>
                        </td>
                        <td data-label="Fecha">
                          <div className="ink-table-cell__primary">
                            {doc.fecha_emision ? formatFiscalDate(doc.fecha_emision) : '-'}
                          </div>
                          <div className="ink-table-cell__meta">{doc.moneda || 'PEN'}</div>
                        </td>
                        <td data-label="Cliente">
                          <div className="ink-table-cell__primary">{clienteName}</div>
                          {clienteDoc && <div className="ink-table-cell__meta">{clienteDoc}</div>}
                        </td>
                        <td data-label="Tipo">
                          <DocumentTypeBadge tipo={doc.tipo_comprobante} size="sm" />
                        </td>
                        <td className="text-right" data-label="Total">
                          <div className="ink-table-cell__primary document-list-amount">
                            {formatCurrency(doc.total_venta, doc.moneda)}
                          </div>
                        </td>
                        <td data-label="Estado">
                          <div className="document-list-status-stack">
                            {sunat ? (
                              <Badge variant={sunat.variant === 'danger' ? 'error' : sunat.variant} title={sunat.tooltip}>
                                {sunat.label}
                              </Badge>
                            ) : (
                              <Badge variant="default">Sin estado</Badge>
                            )}
                            {(doc.provider_verification_status || pdfArtifact || cdrArtifact) && (
                              <div className="document-artifact-stack">
                                {verificationMeta && (
                                  <span className={`document-artifact-pill document-artifact-pill--${verificationMeta.kind}`}>
                                    {verificationMeta.label}
                                  </span>
                                )}
                                {pdfArtifact && (
                                  <span className={`document-artifact-pill document-artifact-pill--${pdfArtifact.kind}`}>
                                    {pdfArtifact.label}
                                  </span>
                                )}
                                {cdrArtifact && (
                                  <span className={`document-artifact-pill document-artifact-pill--${cdrArtifact.kind}`}>
                                    {cdrArtifact.label}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </td>
                        <td data-label="Acciones">
                          <div className="document-list-action-shell">
                            <div className="history-actions-desktop document-list-actions-desktop">
                              {hasFiscalDownload(doc, 'pdf') && (
                                <>
                                  <button
                                    type="button"
                                    className="history-action-button history-action-button--brand"
                                    onClick={() => handleOpenFiscalPdf(doc)}
                                    aria-label={`Ver PDF de ${getFiscalDocumentName(doc)}`}
                                  >
                                    <Eye className="h-4 w-4" />
                                    <span>Ver</span>
                                  </button>
                                  <button
                                    type="button"
                                    className="history-action-button history-action-button--info"
                                    disabled={downloadingId === `${doc.id}-pdf`}
                                    onClick={() => downloadFiscalFile(doc, 'pdf')}
                                    aria-label={`Descargar PDF de ${getFiscalDocumentName(doc)}`}
                                  >
                                    {downloadingId === `${doc.id}-pdf` ? <Spinner size={14} /> : <Download className="h-4 w-4" />}
                                    <span>PDF</span>
                                  </button>
                                </>
                              )}
                              <div className="history-actions-more document-list-actions-more">
                                <button
                                  type="button"
                                  className="history-action-button history-action-button--neutral"
                                  aria-label={`Mas acciones de ${getFiscalDocumentName(doc)}`}
                                  aria-expanded={openActionMenu === desktopMenuKey}
                                  onClick={() => toggleActionMenu(desktopMenuKey)}
                                >
                                  <MoreHorizontal className="h-4 w-4" />
                                  <span>Mas</span>
                                </button>
                                {openActionMenu === desktopMenuKey && (
                                  <div className="history-actions-more-menu document-list-actions-menu">
                                    {hasFiscalDownload(doc, 'xml') && (
                                      <button
                                        type="button"
                                        className="history-actions-mobile-item"
                                        disabled={downloadingId === `${doc.id}-xml`}
                                        onClick={() => runActionMenuItem(() => downloadFiscalFile(doc, 'xml'))}
                                      >
                                        {downloadingId === `${doc.id}-xml` ? <Spinner size={14} /> : <ExternalLink className="h-3.5 w-3.5" />}
                                        Descargar XML
                                      </button>
                                    )}
                                    {hasFiscalDownload(doc, 'cdr') && (
                                      <button
                                        type="button"
                                        className="history-actions-mobile-item"
                                        disabled={downloadingId === `${doc.id}-cdr`}
                                        onClick={() => runActionMenuItem(() => downloadFiscalFile(doc, 'cdr'))}
                                      >
                                        {downloadingId === `${doc.id}-cdr` ? <Spinner size={14} /> : <FileArchive className="h-3.5 w-3.5" />}
                                        Descargar CDR
                                      </button>
                                    )}
                                    {canRetryArtifacts && (
                                      <button
                                        type="button"
                                        className="history-actions-mobile-item"
                                        disabled={retryingArtifactsId === doc.id}
                                        onClick={() => runActionMenuItem(() => handleRetryArtifacts(doc))}
                                      >
                                        {retryingArtifactsId === doc.id ? <Spinner size={14} /> : <RefreshCw className="h-3.5 w-3.5" />}
                                        Reintentar archivos
                                      </button>
                                    )}
                                    <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleCopyShareLink(doc))}>
                                      <Share2 className="h-3.5 w-3.5" />
                                      Copiar enlace
                                    </button>
                                    <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleOpenShareChannel(doc, 'whatsapp'))}>
                                      <MessageCircle className="h-3.5 w-3.5" />
                                      WhatsApp
                                    </button>
                                    <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleOpenShareChannel(doc, 'email'))}>
                                      <Mail className="h-3.5 w-3.5" />
                                      Correo
                                    </button>
                                    <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleOpenCombinedShare(doc))}>
                                      <Send className="h-3.5 w-3.5" />
                                      WhatsApp + correo
                                    </button>
                                    {!doc.sunat_pdf_url && sunat?.kind === 'pending' && (
                                      <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(load)}>
                                        <RefreshCw className="h-3.5 w-3.5" />
                                        Recargar estado
                                      </button>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>

                            <div className="history-actions-mobile document-list-actions-mobile">
                              <button
                                type="button"
                                className="history-action-button history-action-button--neutral"
                                aria-label={`Acciones de ${getFiscalDocumentName(doc)}`}
                                aria-expanded={openActionMenu === mobileMenuKey}
                                onClick={() => toggleActionMenu(mobileMenuKey)}
                              >
                                <MoreHorizontal className="h-4 w-4" />
                                <span>Acciones</span>
                              </button>
                              {openActionMenu === mobileMenuKey && (
                                <div className="history-actions-mobile-menu document-list-actions-menu">
                                  {hasFiscalDownload(doc, 'pdf') && (
                                    <>
                                      <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleOpenFiscalPdf(doc))}>
                                        <Eye className="h-3.5 w-3.5" />
                                        Ver PDF
                                      </button>
                                      <button
                                        type="button"
                                        className="history-actions-mobile-item"
                                        disabled={downloadingId === `${doc.id}-pdf`}
                                        onClick={() => runActionMenuItem(() => downloadFiscalFile(doc, 'pdf'))}
                                      >
                                        {downloadingId === `${doc.id}-pdf` ? <Spinner size={14} /> : <Download className="h-3.5 w-3.5" />}
                                        Descargar PDF
                                      </button>
                                    </>
                                  )}
                                  <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleCopyShareLink(doc))}>
                                    <Share2 className="h-3.5 w-3.5" />
                                    Copiar enlace
                                  </button>
                                  <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleOpenShareChannel(doc, 'whatsapp'))}>
                                    <MessageCircle className="h-3.5 w-3.5" />
                                    WhatsApp
                                  </button>
                                  <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleOpenShareChannel(doc, 'email'))}>
                                    <Mail className="h-3.5 w-3.5" />
                                    Correo
                                  </button>
                                  <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(() => handleOpenCombinedShare(doc))}>
                                    <Send className="h-3.5 w-3.5" />
                                    WhatsApp + correo
                                  </button>
                                  {hasFiscalDownload(doc, 'xml') && (
                                    <button
                                      type="button"
                                      className="history-actions-mobile-item"
                                      disabled={downloadingId === `${doc.id}-xml`}
                                      onClick={() => runActionMenuItem(() => downloadFiscalFile(doc, 'xml'))}
                                    >
                                      {downloadingId === `${doc.id}-xml` ? <Spinner size={14} /> : <ExternalLink className="h-3.5 w-3.5" />}
                                      Descargar XML
                                    </button>
                                  )}
                                  {hasFiscalDownload(doc, 'cdr') && (
                                    <button
                                      type="button"
                                      className="history-actions-mobile-item"
                                      disabled={downloadingId === `${doc.id}-cdr`}
                                      onClick={() => runActionMenuItem(() => downloadFiscalFile(doc, 'cdr'))}
                                    >
                                      {downloadingId === `${doc.id}-cdr` ? <Spinner size={14} /> : <FileArchive className="h-3.5 w-3.5" />}
                                      Descargar CDR
                                    </button>
                                  )}
                                  {canRetryArtifacts && (
                                    <button
                                      type="button"
                                      className="history-actions-mobile-item"
                                      disabled={retryingArtifactsId === doc.id}
                                      onClick={() => runActionMenuItem(() => handleRetryArtifacts(doc))}
                                    >
                                      {retryingArtifactsId === doc.id ? <Spinner size={14} /> : <RefreshCw className="h-3.5 w-3.5" />}
                                      Reintentar archivos
                                    </button>
                                  )}
                                  {!doc.sunat_pdf_url && sunat?.kind === 'pending' && (
                                    <button type="button" className="history-actions-mobile-item" onClick={() => runActionMenuItem(load)}>
                                      <RefreshCw className="h-3.5 w-3.5" />
                                      Recargar estado
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
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
              <span className="ink-table-count">{PER_PAGE} por página</span>
            </div>
          </div>
        )}
      </article>
    </div>
  );
}
