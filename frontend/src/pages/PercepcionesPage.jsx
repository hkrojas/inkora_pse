import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Download,
  Eye,
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

const REGIMEN_OPTS = [
  { value: '01', label: '01 - Venta interna (2%)' },
  { value: '02', label: '02 - Combustible (1%)' },
  { value: '03', label: '03 - Importacion regular (3.5%)' },
];

const REGIMEN_LABELS = {
  '01': 'Venta interna',
  '02': 'Combustible',
  '03': 'Importacion regular',
};

const TASA_POR_REGIMEN = {
  '01': '2.00',
  '02': '1.00',
  '03': '3.50',
};

const TIPO_DOC_OPTS = [
  { value: '01', label: '01 - Factura' },
  { value: '03', label: '03 - Boleta' },
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

function createDetalle(regimen = '01') {
  const fecha = today();
  return {
    tipoDoc: '01',
    numDoc: '',
    fechaEmision: fecha,
    fechaPercepcion: fecha,
    moneda: 'PEN',
    impTotal: '',
    impPercibido: '',
    impCobrar: '',
    cobroImporte: '',
    cobroFecha: fecha,
    tasa: TASA_POR_REGIMEN[regimen] || '2.00',
  };
}

function createForm() {
  return {
    serie: 'P001',
    correlativo: buildCorrelativo(),
    fechaEmision: today(),
    clienteTipoDoc: '6',
    clienteNumDoc: '',
    clienteRznSocial: '',
    regimen: '01',
    tasa: '2.00',
    observacion: 'COMPROBANTE DE PERCEPCION',
    detalles: [createDetalle('01')],
  };
}

function getStatus(percepcion) {
  if (percepcion.status) return percepcion.status;
  if (percepcion.sunatResponse?.success === false || percepcion.sunat_response?.success === false) return 'rejected';
  if (percepcion.sunatResponse?.ticket || percepcion.sunat_response?.ticket) return 'pending';
  return percepcion.sunatResponse?.success ? 'sent' : 'pending';
}

function getStatusBadge(percepcion) {
  const status = getStatus(percepcion);
  if (status === 'rejected') return <Badge variant="error">Rechazado</Badge>;
  if (status === 'pending') return <Badge variant="warning">Pendiente</Badge>;
  return <Badge variant="success">Aceptado</Badge>;
}

function displayNumber(percepcion) {
  const serie = percepcion.serie || percepcion._serie || 'P001';
  const correlativo = percepcion.correlativo || percepcion._correlativo || '';
  return correlativo ? `${serie}-${correlativo}` : serie;
}

function calcDetalle(detalle, tasa) {
  const base = toMoney(detalle.impTotal);
  const rate = toMoney(tasa) / 100;
  const percibido = toMoney(base * rate);
  const cobrar = toMoney(base + percibido);
  return { percibido, cobrar };
}

export default function PercepcionesPage() {
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
      const res = await api.get(`/percepciones/page?${params.toString()}`, { signal });
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
      toast('No se pudo cargar percepciones. Revisa tu conexion e intentalo nuevamente.', 'error');
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

  const setRegimen = (value) => {
    const tasa = TASA_POR_REGIMEN[value] || '2.00';
    setForm((current) => ({
      ...current,
      regimen: value,
      tasa,
      detalles: current.detalles.map((detalle) => {
        const calculated = calcDetalle(detalle, tasa);
        return {
          ...detalle,
          tasa,
          impPercibido: detalle.impTotal ? calculated.percibido.toFixed(2) : detalle.impPercibido,
          impCobrar: detalle.impTotal ? calculated.cobrar.toFixed(2) : detalle.impCobrar,
          cobroImporte: detalle.impTotal ? calculated.cobrar.toFixed(2) : detalle.cobroImporte,
        };
      }),
    }));
  };

  const setDetalle = (index, key) => (event) => {
    const value = event.target.value;
    setForm((current) => {
      const detalles = [...current.detalles];
      const next = { ...detalles[index], [key]: value };
      if (key === 'impTotal') {
        const calculated = calcDetalle(next, current.tasa);
        next.impPercibido = calculated.percibido.toFixed(2);
        next.impCobrar = calculated.cobrar.toFixed(2);
        next.cobroImporte = calculated.cobrar.toFixed(2);
      }
      if (key === 'impCobrar' && !next.cobroImporte) {
        next.cobroImporte = value;
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

  const addDetalle = () => setForm((current) => ({ ...current, detalles: [...current.detalles, createDetalle(current.regimen)] }));
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
        acc.impPercibido += toMoney(detalle.impPercibido);
        acc.impCobrado += toMoney(detalle.impCobrar);
        return acc;
      },
      { impPercibido: 0, impCobrado: 0 },
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
          tipoDoc: form.clienteTipoDoc,
          numDoc: form.clienteNumDoc.trim(),
          rznSocial: form.clienteRznSocial.trim(),
        },
        regimen: form.regimen,
        tasa: toMoney(form.tasa),
        impPercibido: totals.impPercibido,
        impCobrado: totals.impCobrado,
        observacion: form.observacion.trim() || undefined,
        details: form.detalles.map((detalle) => ({
          tipoDoc: detalle.tipoDoc,
          numDoc: detalle.numDoc.trim().toUpperCase(),
          fechaEmision: toApiDate(detalle.fechaEmision),
          impTotal: toMoney(detalle.impTotal),
          moneda: detalle.moneda,
          cobros: [
            {
              moneda: detalle.moneda,
              importe: toMoney(detalle.cobroImporte || detalle.impCobrar),
              fecha: toApiDate(detalle.cobroFecha || detalle.fechaPercepcion),
            },
          ],
          fechaPercepcion: toApiDate(detalle.fechaPercepcion),
          impPercibido: toMoney(detalle.impPercibido),
          impCobrar: toMoney(detalle.impCobrar),
          tipoCambio: {
            fecha: toApiDate(detalle.fechaPercepcion),
            factor: 1,
            monedaObj: detalle.moneda,
            monedaRef: detalle.moneda,
          },
        })),
      };

      const res = await api.post('/percepciones/emitir', payload);
      setResultados((prev) => [res, ...prev].slice(0, PER_PAGE));
      toast(res.ticket ? `Ticket: ${res.ticket}` : 'Percepcion emitida correctamente', 'success');
      setModalOpen(false);
    } catch (err) {
      toast(err?.message || 'No se pudo emitir la percepcion. Revisa los datos e intentalo nuevamente.', 'error');
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
      label: 'Percepciones',
      text: `${tabCounts.all} registradas`,
      link: 'Ver todos',
      icon: <Eye size={16} />,
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
    <div className="page-shell page-shell--dense percepciones-page">
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
            Nueva percepcion
          </button>
        </div>
      </div>

      <section className="attention document-list-hero ink-enter-2">
        <div className="attention-title document-list-hero-title">
          <div className="document-list-hero-head">
            <div className="attention-title-badge">
              <Eye size={15} />
            </div>
          </div>

          <div className="document-list-hero-pagecopy">
            <h2>Percepciones</h2>
            <p>Comprobantes de percepcion como agente perceptor ante SUNAT.</p>
          </div>

          <div className="document-list-hero-kicker">
            Tipo 40 - regimen {form.regimen} tasa {form.tasa}%
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
              placeholder="Buscar por serie, correlativo o cliente..."
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
            <strong>{total}</strong> percepciones
          </div>
        </div>

        {loading ? (
          <div className="document-list-loading">
            <Spinner size={22} />
            Cargando percepciones...
          </div>
        ) : filtered.length === 0 ? (
          <div className="document-list-empty">
            <EmptyState
              icon={<Eye size={22} />}
              title={hasActiveFilters ? 'Sin resultados para estos filtros' : 'Aun no tienes percepciones emitidas'}
              description={
                hasActiveFilters
                  ? 'Ajusta la busqueda o el rango de fechas.'
                  : 'Emite la primera percepcion usando datos validados para APISPeru/SUNAT.'
              }
              action={
                hasActiveFilters ? (
                  <button className="btn-secondary" onClick={clearFilters}>
                    Limpiar filtros
                  </button>
                ) : (
                  <button className="btn-primary" onClick={handleOpen}>
                    <Plus size={15} />
                    Nueva percepcion
                  </button>
                )
              }
            />
          </div>
        ) : (
          <div className="ink-table-card document-list-table">
            <div className="ink-table-header">
              <div className="ink-table-title">
                <strong>Percepciones emitidas</strong>
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
              <table className="ink-table ink-percepcion-table">
                <thead>
                  <tr>
                    <th>Numero</th>
                    <th>Cliente</th>
                    <th>Regimen</th>
                    <th>Percibido</th>
                    <th>Cobrado</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((percepcion) => (
                    <tr key={percepcion.id || displayNumber(percepcion)}>
                      <td data-label="Numero">
                        <div className="ink-table-cell__primary document-list-folio">{displayNumber(percepcion)}</div>
                        <div className="ink-table-cell__meta">Tipo 40 - Percepcion</div>
                      </td>
                      <td data-label="Cliente">
                        <div className="ink-table-cell__primary">{percepcion.cliente_rzn_social || '-'}</div>
                        <div className="ink-table-cell__meta">{percepcion.cliente_num_doc || '-'}</div>
                      </td>
                      <td data-label="Regimen">
                        <div className="ink-table-cell__primary">{REGIMEN_LABELS[percepcion.regimen] || percepcion.regimen}</div>
                        <div className="ink-table-cell__meta">Tasa {formatMoney(percepcion.tasa)}%</div>
                      </td>
                      <td data-label="Percibido">
                        <div className="ink-table-cell__primary" style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                          S/ {formatMoney(percepcion.imp_percibido)}
                        </div>
                      </td>
                      <td data-label="Cobrado">
                        <div className="ink-table-cell__primary" style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                          S/ {formatMoney(percepcion.imp_cobrado)}
                        </div>
                      </td>
                      <td data-label="Estado">
                        {getStatusBadge(percepcion)}
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
        title="Nueva percepcion"
        subtitle="Registra un comprobante tipo 40 con los campos exigidos por APISPeru y SUNAT."
        icon={<Eye size={22} />}
        footer={(
          <>
            <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" form="percepcion-form" className="btn-primary" disabled={submitting}>
              {submitting && <Spinner size={14} />}
              Emitir percepcion
            </button>
          </>
        )}
      >
        <form id="percepcion-form" onSubmit={handleSubmit} className="drawer-editor-form">
          <div className="drawer-editor-section">
            <div className="drawer-editor-section-header">
              <p>Cabecera fiscal</p>
            </div>
            <p className="drawer-editor-section-intro">
              SUNAT usa el comprobante tipo 40. La serie debe iniciar con P y la tasa depende del regimen.
            </p>
            <div className="responsive-form-grid-3">
              <div>
                <label className="label">Serie <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.serie} onChange={setInput('serie')} placeholder="P001" required maxLength={4} />
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
              <p>Cliente sujeto a percepcion</p>
            </div>
            <p className="drawer-editor-section-intro">
              APISPeru recibe este bloque como proveedor en su contrato, pero representa al cliente percibido.
            </p>
            <div className="responsive-form-grid-120-1-2">
              <div>
                <label className="label">Tipo doc</label>
                <CustomSelect
                  value={form.clienteTipoDoc}
                  onChange={setField('clienteTipoDoc')}
                  options={[{ value: '6', label: '6 - RUC' }, { value: '1', label: '1 - DNI' }]}
                />
              </div>
              <div>
                <label className="label">Numero <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.clienteNumDoc} onChange={setInput('clienteNumDoc')} placeholder="20xxxxxxxxx" required maxLength={11} />
              </div>
              <div>
                <label className="label">Razon social / Nombre <span style={{ color: 'var(--color-error)' }}>*</span></label>
                <input className="input" value={form.clienteRznSocial} onChange={setInput('clienteRznSocial')} placeholder="Cliente SAC" required maxLength={180} />
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
                <CustomSelect value={form.regimen} onChange={setRegimen} options={REGIMEN_OPTS} />
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
              Total percibido: <strong>S/ {formatMoney(totals.impPercibido)}</strong> - Cobrado total:{' '}
              <strong>S/ {formatMoney(totals.impCobrado)}</strong>
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
              APISPeru espera numDoc con formato SERIE-CORRELATIVO y al menos un cobro asociado.
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
                      <label className="label" style={{ fontSize: 10 }}>F. percepcion</label>
                      <input className="input" type="date" value={detalle.fechaPercepcion} onChange={setDetalle(index, 'fechaPercepcion')} required />
                    </div>
                  </div>

                  <div className="responsive-form-grid-1-1-1-auto">
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Total sin percepcion</label>
                      <input className="input" type="number" step="0.01" value={detalle.impTotal} onChange={setDetalle(index, 'impTotal')} placeholder="0.00" required />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Monto percibido</label>
                      <input className="input" type="number" step="0.01" value={detalle.impPercibido} onChange={setDetalle(index, 'impPercibido')} placeholder="0.00" required />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Importe a cobrar</label>
                      <input className="input" type="number" step="0.01" value={detalle.impCobrar} onChange={setDetalle(index, 'impCobrar')} placeholder="0.00" required />
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
                      <label className="label" style={{ fontSize: 10 }}>Cobro registrado</label>
                      <input className="input" type="number" step="0.01" value={detalle.cobroImporte} onChange={setDetalle(index, 'cobroImporte')} placeholder="0.00" required />
                    </div>
                    <div>
                      <label className="label" style={{ fontSize: 10 }}>Fecha cobro</label>
                      <input className="input" type="date" value={detalle.cobroFecha} onChange={setDetalle(index, 'cobroFecha')} required />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="proto-alert info drawer-editor-note" style={{ fontSize: 12 }}>
            <strong>Endpoint:</strong> POST /perception/send - tipoDoc SUNAT 40 - regimen 01/02/03.
          </div>
        </form>
      </Drawer>
    </div>
  );
}
