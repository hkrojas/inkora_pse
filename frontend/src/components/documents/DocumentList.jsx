import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Download, ExternalLink, FileText, Plus, RefreshCw, Search, XCircle } from 'lucide-react';
import { api } from '../../lib/utils/api';
import { useToast } from '../ui/Toast';
import Spinner from '../ui/Spinner';
import Badge from '../ui/Badge';
import CustomSelect from '../ui/CustomSelect';
import DatePicker from '../ui/DatePicker';
import { DocumentTypeBadge } from './DocumentType';
import { getSunatStatus, formatCurrency } from '../../lib/utils/documents';

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'aceptado', label: 'Aceptado' },
  { value: 'pendiente', label: 'Pendiente' },
  { value: 'error', label: 'Error SUNAT' },
  { value: 'anulado', label: 'Anulado' },
];

const MONEDA_OPTIONS = [
  { value: 'all', label: 'Todas' },
  { value: 'PEN', label: 'S/ Soles' },
  { value: 'USD', label: '$ Dolares' },
];

const PER_PAGE = 25;

// Filterable, searchable document list for Facturas / Boletas / Notas
// Props: tipo ('01'|'03'|'07'|'08'), title, subtitle, newLabel, newHref, endpoint
export default function DocumentList({ tipo, title, subtitle, newLabel, newHref, endpoint }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({ desde: '', hasta: '', estado: 'all', moneda: 'all' });
  const [page, setPage] = useState(1);
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = endpoint || '/facturas-emitidas/';
      const all = await api.get(url);
      const filtered = tipo ? all.filter((d) => d.tipo_comprobante === tipo) : all;
      setDocs(filtered);
    } catch {
      toast('No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error');
    } finally {
      setLoading(false);
    }
  }, [tipo, endpoint, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPage(1);
  }, [search, filters]);

  const setFilter = (k, v) => setFilters((f) => ({ ...f, [k]: v }));
  const clearFilters = () => {
    setFilters({ desde: '', hasta: '', estado: 'all', moneda: 'all' });
    setSearch('');
  };

  const filtered = useMemo(() => {
    return docs.filter((d) => {
      const q = search.toLowerCase();
      const matchSearch = !q
        || (d.cliente?.razon_social || d.cliente?.nombre || '').toLowerCase().includes(q)
        || (d.cliente?.numero_documento || '').includes(q)
        || (`${d.serie}-${d.correlativo}`).toLowerCase().includes(q);
      const matchDesde = !filters.desde || new Date(d.fecha_emision) >= new Date(filters.desde);
      const matchHasta = !filters.hasta || new Date(d.fecha_emision) <= new Date(filters.hasta);
      const sunatSt = getSunatStatus(d);
      const matchEstado = filters.estado === 'all'
        || (filters.estado === 'aceptado' && sunatSt?.kind === 'ok')
        || (filters.estado === 'pendiente' && sunatSt?.kind === 'pending')
        || (filters.estado === 'error' && sunatSt?.kind === 'error')
        || (filters.estado === 'anulado' && sunatSt?.kind === 'voided');
      const matchMoneda = filters.moneda === 'all' || d.moneda === filters.moneda;
      return matchSearch && matchDesde && matchHasta && matchEstado && matchMoneda;
    });
  }, [docs, search, filters]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const pageItems = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  const hasActiveFilters = (
    search
    || filters.desde
    || filters.hasta
    || filters.estado !== 'all'
    || filters.moneda !== 'all'
  );

  const handleExport = () => {
    toast('La exportación está en desarrollo.', 'info');
  };

  return (
    <div className="page-shell">
      {/* Topbar */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <h1 className="page-title">{title}</h1>
          <span
            className="tx-meta"
            style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              fontSize: 'var(--fs-micro)',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              padding: '4px 10px',
              border: '1px solid var(--border-rule)',
              background: 'var(--bg-surface-2)',
              color: 'var(--text-tertiary)',
            }}
          >
            {filtered.length} de {docs.length}
          </span>
          {subtitle && (
            <p className="tx-meta" style={{ margin: 0, color: 'var(--text-muted)' }}>
              {subtitle}
            </p>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button type="button" className="btn-secondary" onClick={handleExport}>
            <Download size={16} />
            EXPORTAR
          </button>
          {newHref && (
            <Link className="btn-primary" to={newHref}>
              <Plus size={16} />
              {newLabel || 'NUEVO'}
            </Link>
          )}
        </div>
      </div>

      {/* Sticky filters */}
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          background: 'var(--bg-app)',
          borderBottom: '1px solid var(--border-hair)',
          padding: '12px 0',
          marginBottom: '16px',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr repeat(4, auto) auto',
            gap: '10px',
            alignItems: 'end',
          }}
        >
          <div className="ink-search" style={{ position: 'relative' }}>
            <Search
              size={14}
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
                pointerEvents: 'none',
              }}
            />
            <input
              className="input-compact"
              style={{ paddingLeft: '36px', width: '100%' }}
              placeholder="Buscar por folio, cliente o documento..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label className="tx-label">Estado</label>
            <CustomSelect
              compact
              value={filters.estado}
              onChange={(v) => setFilter('estado', v)}
              options={STATUS_OPTIONS}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label className="tx-label">Moneda</label>
            <CustomSelect
              compact
              value={filters.moneda}
              onChange={(v) => setFilter('moneda', v)}
              options={MONEDA_OPTIONS}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label className="tx-label">Desde</label>
            <DatePicker compact value={filters.desde} onChange={(v) => setFilter('desde', v)} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label className="tx-label">Hasta</label>
            <DatePicker compact value={filters.hasta} onChange={(v) => setFilter('hasta', v)} />
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              className="btn-ghost"
              onClick={clearFilters}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                height: '36px',
                whiteSpace: 'nowrap',
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--fs-micro)',
                fontWeight: 700,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
              }}
            >
              <XCircle size={14} />
              LIMPIAR FILTROS
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '80px 0' }}>
          <Spinner size="lg" />
        </div>
      ) : filtered.length === 0 ? (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '80px 20px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: '64px',
              height: '64px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1.5px solid var(--ink-200)',
              color: 'var(--ink-300)',
              marginBottom: '20px',
            }}
          >
            <FileText size={28} strokeWidth={1.5} />
          </div>
          <h3
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: 'var(--fs-h3)',
              fontWeight: 700,
              color: 'var(--text-primary)',
              marginBottom: '8px',
            }}
          >
            {hasActiveFilters ? 'Sin resultados para estos filtros' : 'Aún no tienes comprobantes emitidos'}
          </h3>
          <p
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: 'var(--fs-body)',
              color: 'var(--text-secondary)',
              maxWidth: '360px',
              marginBottom: '20px',
            }}
          >
            {hasActiveFilters
              ? 'Prueba ajustar los filtros o limpia la búsqueda para ver más resultados.'
              : 'Crea tu primera factura o boleta usando un cliente registrado o una cotización aprobada.'}
          </p>
          {hasActiveFilters ? (
            <button className="btn-secondary" onClick={clearFilters}>
              Limpiar filtros
            </button>
          ) : newHref ? (
            <Link className="btn-primary" to={newHref}>
              <Plus size={16} />
              {newLabel || 'Nuevo'}
            </Link>
          ) : null}
        </div>
      ) : (
        <div className="ink-card" style={{ padding: 0, overflow: 'hidden', border: '1px solid var(--border-rule)' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="ink-table" style={{ width: '100%', borderCollapse: 'collapse', minWidth: '720px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--ink-900)' }}>
                <th className="ink-th" style={{ textAlign: 'left', padding: '12px 16px' }}>
                  <span className="tx-label">Folio</span>
                </th>
                <th className="ink-th" style={{ textAlign: 'left', padding: '12px 16px' }}>
                  <span className="tx-label">Fecha</span>
                </th>
                <th className="ink-th" style={{ textAlign: 'left', padding: '12px 16px' }}>
                  <span className="tx-label">Cliente</span>
                </th>
                <th className="ink-th" style={{ textAlign: 'left', padding: '12px 16px' }}>
                  <span className="tx-label">Tipo</span>
                </th>
                <th className="ink-th" style={{ textAlign: 'right', padding: '12px 16px' }}>
                  <span className="tx-label">Total</span>
                </th>
                <th className="ink-th" style={{ textAlign: 'left', padding: '12px 16px' }}>
                  <span className="tx-label">Estado SUNAT</span>
                </th>
                <th className="ink-th" style={{ textAlign: 'right', padding: '12px 16px' }}>
                  <span className="tx-label">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map((doc) => {
                const sunatSt = getSunatStatus(doc);
                const num = `${doc.serie}-${String(doc.correlativo).padStart(8, '0')}`;
                const clienteName = doc.cliente?.razon_social || doc.cliente?.nombre || '-';
                const clienteDoc = doc.cliente?.numero_documento || doc.cliente?.ruc || doc.cliente?.dni;
                const isAceptado = sunatSt?.kind === 'ok';

                return (
                  <tr
                    key={doc.id}
                    style={{
                      borderBottom: '1px solid var(--border-hair)',
                      transition: 'background 120ms ease',
                      borderLeft: isAceptado ? '2px solid var(--sx-success)' : '2px solid transparent',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--bg-surface-2)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <td className="ink-td" style={{ padding: '12px 16px' }}>
                      <span className="tx-folio">{num}</span>
                    </td>
                    <td className="ink-td" style={{ padding: '12px 16px' }}>
                      <span className="tx-meta">
                        {doc.fecha_emision ? new Date(doc.fecha_emision).toLocaleDateString('es-PE') : '-'}
                      </span>
                    </td>
                    <td className="ink-td" style={{ padding: '12px 16px' }}>
                      <p style={{ fontFamily: 'var(--font-body)', fontWeight: 600, fontSize: 'var(--fs-body)', margin: 0 }}>
                        {clienteName}
                      </p>
                      {clienteDoc && (
                        <p className="tx-meta" style={{ margin: 0 }}>{clienteDoc}</p>
                      )}
                    </td>
                    <td className="ink-td" style={{ padding: '12px 16px' }}>
                      <DocumentTypeBadge tipo={doc.tipo_comprobante} size="sm" />
                    </td>
                    <td className="ink-td" style={{ padding: '12px 16px', textAlign: 'right' }}>
                      <span className="tx-amount">{formatCurrency(doc.total_venta, doc.moneda)}</span>
                    </td>
                    <td className="ink-td" style={{ padding: '12px 16px' }}>
                      {sunatSt ? (
                        <Badge
                          variant={sunatSt.variant === 'danger' ? 'error' : sunatSt.variant}
                          title={sunatSt.tooltip}
                        >
                          {sunatSt.label}
                        </Badge>
                      ) : (
                        <Badge variant="default">-</Badge>
                      )}
                    </td>
                    <td className="ink-td" style={{ padding: '12px 16px' }}>
                      <div className="ink-row-actions" style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '6px' }}>
                        {doc.sunat_pdf_url && (
                          <a
                            href={doc.sunat_pdf_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn-icon"
                            title="Ver PDF SUNAT"
                            style={{ width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                          >
                            <ExternalLink size={14} />
                          </a>
                        )}
                        <Link
                          to={`/cotizaciones/${doc.id}`}
                          className="btn-icon"
                          title="Ver detalle"
                          style={{ width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          <FileText size={14} />
                        </Link>
                        {!doc.sunat_pdf_url && sunatSt?.kind === 'pending' && (
                          <button
                            type="button"
                            className="btn-icon"
                            title="Recargar estado SUNAT"
                            onClick={load}
                            style={{ width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                          >
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

          {/* Sticky pagination footer */}
          {totalPages > 1 && (
            <div
              style={{
                position: 'sticky',
                bottom: 0,
                background: 'var(--bg-app)',
                borderTop: '1px solid var(--border-hair)',
                padding: '12px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--fs-xs)',
                  fontWeight: 600,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                  color: 'var(--text-tertiary)',
                }}
              >
                PAG. {page} / {totalPages}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  className="btn-icon"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  style={{
                    width: '36px',
                    height: '36px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: page <= 1 ? 0.45 : 1,
                    cursor: page <= 1 ? 'not-allowed' : 'pointer',
                  }}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700 }}>{'<'}</span>
                </button>
                <button
                  type="button"
                  className="btn-icon"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  style={{
                    width: '36px',
                    height: '36px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: page >= totalPages ? 0.45 : 1,
                    cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                  }}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700 }}>{'>'}</span>
                </button>
              </div>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--fs-xs)',
                  fontWeight: 600,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                  color: 'var(--text-tertiary)',
                }}
              >
                MOSTRAR: {PER_PAGE}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
