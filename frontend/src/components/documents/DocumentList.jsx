import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, FileText, RefreshCw, Search, XCircle } from 'lucide-react';
import { api } from '../../lib/utils/api';
import { useToast } from '../ui/Toast';
import Spinner from '../ui/Spinner';
import Badge from '../ui/Badge';
import EmptyState from '../ui/EmptyState';
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

// Filterable, searchable document list for Facturas / Boletas / Notas
// Props: tipo ('01'|'03'|'07'|'08'), title, subtitle, newLabel, newHref, endpoint
export default function DocumentList({ tipo, title, subtitle, newLabel, newHref, endpoint }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({ desde: '', hasta: '', estado: 'all', moneda: 'all' });
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = endpoint || '/facturas-emitidas/';
      const all = await api.get(url);
      const filtered = tipo ? all.filter((d) => d.tipo_comprobante === tipo) : all;
      setDocs(filtered);
    } catch {
      toast('Error al cargar documentos', 'error');
    } finally {
      setLoading(false);
    }
  }, [tipo, endpoint, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const setFilter = (k, v) => setFilters((f) => ({ ...f, [k]: v }));
  const clearFilters = () => {
    setFilters({ desde: '', hasta: '', estado: 'all', moneda: 'all' });
    setSearch('');
  };

  const filtered = docs.filter((d) => {
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

  const hasActiveFilters = (
    search
    || filters.desde
    || filters.hasta
    || filters.estado !== 'all'
    || filters.moneda !== 'all'
  );

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1 className="page-title">{title}</h1>
          <p className="page-subtitle">
            {subtitle || `${docs.length} documento${docs.length !== 1 ? 's' : ''} encontrado${docs.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        {newHref && (
          <Link className="btn-primary" to={newHref}>
            {newLabel || 'Nuevo'}
          </Link>
        )}
      </div>

      <div className="ink-card" style={{ padding: '12px 16px', marginBottom: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr repeat(4, auto) auto', gap: '10px', alignItems: 'end' }}>
          <div style={{ position: 'relative' }}>
            <Search
              size={13}
              style={{
                position: 'absolute',
                left: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#94A3B8',
                pointerEvents: 'none',
              }}
            />
            <input
              className="input-compact"
              style={{ paddingLeft: '30px' }}
              placeholder="Buscar por cliente, numero..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label style={{ fontSize: '10px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Desde
            </label>
            <DatePicker compact value={filters.desde} onChange={(v) => setFilter('desde', v)} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label style={{ fontSize: '10px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Hasta
            </label>
            <DatePicker compact value={filters.hasta} onChange={(v) => setFilter('hasta', v)} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label style={{ fontSize: '10px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Estado
            </label>
            <CustomSelect
              compact
              value={filters.estado}
              onChange={(v) => setFilter('estado', v)}
              options={STATUS_OPTIONS}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label style={{ fontSize: '10px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Moneda
            </label>
            <CustomSelect
              compact
              value={filters.moneda}
              onChange={(v) => setFilter('moneda', v)}
              options={MONEDA_OPTIONS}
            />
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: '#DC2626',
                background: '#FEF2F2',
                border: '1px solid #FECACA',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                height: '36px',
              }}
            >
              <XCircle size={12} /> Limpiar
            </button>
          )}
        </div>

        {hasActiveFilters && (
          <p style={{ marginTop: '8px', fontSize: '11px', color: '#64748B' }}>
            Mostrando <strong>{filtered.length}</strong> de {docs.length} documentos
          </p>
        )}
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <Spinner size="lg" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title={hasActiveFilters ? 'Sin resultados' : 'Sin documentos emitidos'}
          description={hasActiveFilters ? 'Ajusta los filtros para ver mas resultados.' : 'Los documentos emitidos a SUNAT apareceran aqui.'}
          action={hasActiveFilters ? (
            <button className="btn-secondary" onClick={clearFilters}>Limpiar filtros</button>
          ) : newHref ? (
            <Link className="btn-primary" to={newHref}>{newLabel || 'Nuevo'}</Link>
          ) : undefined}
        />
      ) : (
        <div className="ink-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="ink-table">
            <thead>
              <tr>
                <th className="ink-th">Numero</th>
                <th className="ink-th">Tipo</th>
                <th className="ink-th">Fecha</th>
                <th className="ink-th">Cliente</th>
                <th className="ink-th" style={{ textAlign: 'right' }}>Total</th>
                <th className="ink-th">Estado SUNAT</th>
                <th className="ink-th" style={{ textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc) => {
                const sunatSt = getSunatStatus(doc);
                const num = `${doc.serie}-${String(doc.correlativo).padStart(8, '0')}`;
                const clienteName = doc.cliente?.razon_social || doc.cliente?.nombre || '-';
                const clienteDoc = doc.cliente?.numero_documento || doc.cliente?.ruc || doc.cliente?.dni;

                return (
                  <tr key={doc.id} className="ink-tr">
                    <td className="ink-td">
                      <span className="font-mono-label text-xs">{num}</span>
                    </td>
                    <td className="ink-td">
                      <DocumentTypeBadge tipo={doc.tipo_comprobante} size="sm" />
                    </td>
                    <td className="ink-td" style={{ fontSize: 12 }}>
                      {doc.fecha_emision ? new Date(doc.fecha_emision).toLocaleDateString('es-PE') : '-'}
                    </td>
                    <td className="ink-td">
                      <p style={{ fontWeight: 600, fontSize: 13 }}>{clienteName}</p>
                      {clienteDoc && <p style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{clienteDoc}</p>}
                    </td>
                    <td className="ink-td" style={{ textAlign: 'right' }}>
                      <span className="font-mono-label text-xs">{formatCurrency(doc.total_venta, doc.moneda)}</span>
                    </td>
                    <td className="ink-td">
                      {sunatSt ? (
                        <Badge variant={sunatSt.variant === 'danger' ? 'error' : sunatSt.variant} title={sunatSt.tooltip}>
                          {sunatSt.label}
                        </Badge>
                      ) : (
                        <Badge variant="default">-</Badge>
                      )}
                    </td>
                    <td className="ink-td">
                      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '4px' }}>
                        {doc.sunat_pdf_url && (
                          <a
                            href={doc.sunat_pdf_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="row-action-icon"
                            title="Ver PDF SUNAT"
                            style={{ background: '#F1F5F9', color: '#475569' }}
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                        <Link
                          to={`/cotizaciones/${doc.id}`}
                          className="row-action-icon"
                          title="Ver detalle"
                          style={{ background: 'var(--inkora-primary)', color: '#fff' }}
                        >
                          <FileText size={12} />
                        </Link>
                        {!doc.sunat_pdf_url && sunatSt?.kind === 'pending' && (
                          <button
                            type="button"
                            className="row-action-icon"
                            title="Recargar estado SUNAT"
                            style={{ background: '#FEF3C7', color: '#D97706' }}
                            onClick={load}
                          >
                            <RefreshCw size={12} />
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
      )}
    </div>
  );
}
