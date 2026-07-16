import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  CircleAlert,
  CreditCard,
  FileText,
  Send,
  Wallet,
} from 'lucide-react';
import { dashboard } from '../services/dashboard';
import OperationalPageHeader from '../components/ui/OperationalPageHeader';

function safeNumber(value) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatShortDate(date) {
  if (!date) return '--';
  return new Date(date).toLocaleDateString('es-PE', {
    day: '2-digit',
    month: 'short',
  });
}

function formatDashboardMonth() {
  return new Date().toLocaleDateString('es-PE', {
    month: 'long',
    year: 'numeric',
  }).replace(/^(\w)/, (c) => c.toUpperCase());
}

function formatDocNumber(doc) {
  if (doc?.serie && doc?.correlativo) {
    return `${doc.serie}-${String(doc.correlativo).padStart(6, '0')}`;
  }
  if (doc?.numero) return doc.numero;
  if (doc?.codigo) return doc.codigo;
  return 'Sin número';
}

function getDocClient(doc) {
  return (
    doc?.cliente?.razon_social ||
    doc?.cliente?.nombre ||
    doc?.cliente_nombre ||
    doc?.razon_social ||
    'Cliente sin nombre'
  );
}

function getDocAmount(doc) {
  if (doc?.saldo_pendiente != null) return safeNumber(doc.saldo_pendiente);
  if (doc?.total_venta != null) return safeNumber(doc.total_venta);
  if (doc?.monto_pagado != null) return safeNumber(doc.monto_pagado);
  return 0;
}

function getStatusMeta(status) {
  const value = String(status || '').toLowerCase();
  if (['cobrado', 'pagado', 'aceptado', 'aceptada', 'emitido', 'emitida'].includes(value)) {
    return { label: status || 'Cobrado', tone: 'ok' };
  }
  if (['pendiente', 'parcial', 'por vencer', 'borrador', 'sin emitir', 'por enviar'].includes(value)) {
    return { label: status || 'Pendiente', tone: 'warn' };
  }
  if (['rechazado', 'rechazada', 'anulado', 'anulada', 'vencido', 'vencida'].includes(value)) {
    return { label: status || 'Vencido', tone: 'bad' };
  }
  return { label: status || 'Activo', tone: 'neutral' };
}

function getDaysLate(doc) {
  if (!doc?.fecha_vencimiento) return null;
  const due = new Date(doc.fecha_vencimiento);
  if (Number.isNaN(due.getTime())) return null;
  const diff = Math.floor((Date.now() - due.getTime()) / 86400000);
  return diff > 0 ? diff : 0;
}

function percent(value, total) {
  if (!total) return 0;
  return Math.max(0, Math.min(100, Math.round((value / total) * 100)));
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [cobranza, setCobranza] = useState(null);
  const [recentDocs, setRecentDocs] = useState([]);
  const [overdueDocs, setOverdueDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDashboard = useCallback(() => {
    setLoading(true);
    setError('');
    Promise.allSettled([
      dashboard.stats(),
      dashboard.cobranzaResumen(),
      dashboard.recentDocuments(),
      dashboard.pendingInvoices(),
    ])
      .then(([statsResult, cobranzaResult, recentResult, overdueResult]) => {
        const statsData = statsResult.status === 'fulfilled' ? statsResult.value : null;
        const cobranzaData = cobranzaResult.status === 'fulfilled' ? cobranzaResult.value : null;
        const recentData = recentResult.status === 'fulfilled' ? recentResult.value : [];
        const overdueData = overdueResult.status === 'fulfilled' ? overdueResult.value : [];
        const sortedRecent = Array.isArray(recentData)
          ? [...recentData].sort((a, b) => {
              const aTime = new Date(a?.fecha_emision || a?.created_at || 0).getTime();
              const bTime = new Date(b?.fecha_emision || b?.created_at || 0).getTime();
              return bTime - aTime;
            })
          : [];

        const sortedOverdue = Array.isArray(overdueData)
          ? [...overdueData].sort((a, b) => {
              const aTime = new Date(a?.fecha_vencimiento || a?.fecha_emision || 0).getTime();
              const bTime = new Date(b?.fecha_vencimiento || b?.fecha_emision || 0).getTime();
              return aTime - bTime;
            })
          : [];

        setStats(statsData);
        setCobranza(cobranzaData);
        setRecentDocs(sortedRecent);
        setOverdueDocs(sortedOverdue);

        const failed = [statsResult, cobranzaResult, recentResult, overdueResult].filter(
          (result) => result.status === 'rejected',
        ).length;
        if (failed === 4) {
          setError('No se pudo cargar el dashboard. Revisa tu conexión e inténtalo nuevamente.');
        } else if (failed > 0) {
          setError('Algunas métricas no respondieron. Los datos visibles pueden estar incompletos.');
        }
      })
      .catch(() => {
        setError('No se pudo cargar el dashboard. Revisa tu conexión e inténtalo nuevamente.');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  if (loading) {
    return (
      <div style={{ padding: '28px 26px 36px' }}>
        <div style={{ display: 'grid', gap: '16px' }}>
          <div className="skeleton" style={{ height: '40px', width: '60%', borderRadius: '12px' }} />
          <div className="skeleton" style={{ height: '160px', borderRadius: '22px' }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton" style={{ height: '142px', borderRadius: '18px' }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const cobrosRegistradosHistoricos = safeNumber(stats?.ingresos_totales);
  const totalCobradoMes = safeNumber(cobranza?.total_pagado_mes);
  const totalPorCobrar = safeNumber(cobranza?.total_por_cobrar ?? stats?.saldos_por_cobrar);
  const saldoVencido = safeNumber(cobranza?.total_vencido ?? stats?.saldo_vencido);
  const documentosPendientes = safeNumber(cobranza?.documentos_pendientes);
  const documentosVencidos = safeNumber(cobranza?.documentos_vencidos);
  const clientesConDeuda = safeNumber(cobranza?.clientes_con_deuda ?? overdueDocs.length);
  const docsRechazados = [...recentDocs, ...overdueDocs].filter(
    (doc) => getStatusMeta(doc?.estado).tone === 'bad',
  ).length;
  const cotizacionesPendientes = recentDocs.filter(
    (doc) => doc?.document_kind === 'quotation' && getStatusMeta(doc?.estado).tone !== 'ok',
  ).length;

  const porVencer = Math.max(totalPorCobrar - saldoVencido, 0);
  const totalAging = Math.max(totalPorCobrar, 1);
  const documentosConDeuda = documentosPendientes + documentosVencidos;
  const headerSummary = documentosConDeuda > 0
    ? `${documentosConDeuda} documentos con saldo pendiente${cotizacionesPendientes > 0 ? ` y ${cotizacionesPendientes} cotizaciones por seguir.` : '.'}`
    : cotizacionesPendientes > 0
      ? `${cotizacionesPendientes} cotizaciones recientes esperan seguimiento.`
      : 'Revisa caja, emisión fiscal y seguimiento comercial en un solo lugar.';

  const attentionCards = [
    {
      value: documentosConDeuda,
      label: 'Documentos fiscales con saldo pendiente.',
      detail: `${clientesConDeuda} clientes${documentosVencidos > 0 ? ` · ${documentosVencidos} vencidos` : ' · sin vencidos'}`,
      action: 'Abrir cobranza',
      href: '/cobranza',
    },
    {
      value: docsRechazados,
      label: 'Alertas en documentos visibles.',
      detail: 'Revisa los estados que requieren corrección.',
      action: 'Ver documentos',
      href: '/facturas',
    },
    {
      value: cotizacionesPendientes,
      label: 'Cotizaciones recientes pendientes.',
      detail: 'Da seguimiento antes de que pierdan vigencia.',
      action: 'Dar seguimiento',
      href: '/cotizaciones',
    },
  ];
  const actionableAttentionCards = attentionCards.filter((item) => item.value > 0);

  const urgentItems = overdueDocs.slice(0, 3);

  return (
    <div className="dashboard-page">
      <OperationalPageHeader
        variant="monitoring"
        eyebrow="Centro operativo"
        title="Resumen operativo"
        description={headerSummary}
        meta={<span className="operational-page-header__scope">Vista consolidada del negocio</span>}
        actions={
          <span className="dashboard-period" aria-label={`Periodo actual: ${formatDashboardMonth()}`}>
            <CalendarDays size={16} />
            {formatDashboardMonth()}
          </span>
        }
      />

      {error && (
        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', padding: '12px 16px', borderRadius: '14px', background: 'var(--color-danger-soft)', color: 'var(--color-danger-text)', fontSize: '13px', marginBottom: '16px' }}>
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '1px' }} />
          <span>{error}</span>
          <button type="button" className="btn-secondary" onClick={loadDashboard}>
            Reintentar
          </button>
        </div>
      )}

      <section
        className="attention ink-enter-2"
        style={{ '--attention-cards': Math.max(actionableAttentionCards.length, 1) }}
        aria-labelledby="dashboard-attention-title"
      >
        <div className="attention-title">
          <span className="attention-title-badge">
            <CircleAlert size={16} />
          </span>
          <h3 id="dashboard-attention-title">Prioridades de hoy</h3>
          <p>Solo acciones que impactan caja, emisión fiscal o seguimiento comercial.</p>
        </div>
        {actionableAttentionCards.map((item) => (
          <button
            type="button"
            key={item.label}
            className="attention-card"
            onClick={() => navigate(item.href)}
          >
            <strong>{item.value}</strong>
            <span className="attention-card-text">{item.label}</span>
            <span className="attention-card-detail">{item.detail}</span>
            <span className="attention-card-link">
              {item.action}
              <ArrowRight size={13} />
            </span>
          </button>
        ))}
        {actionableAttentionCards.length === 0 && (
          <div className="attention-card attention-card--calm">
            <strong>Todo al día</strong>
            <span className="attention-card-text">No hay alertas comerciales o fiscales que requieran una acción inmediata.</span>
          </div>
        )}
      </section>

      <section className="metrics-grid metrics-grid--core" aria-label="Indicadores de caja y cobranza">
        <article className="metric-card ink-enter-3">
          <div className="metric-top">
            <div className="metric-label">Cobros registrados</div>
            <span className="metric-badge neutral">Historico</span>
          </div>
          <div className="metric-value">
            {cobrosRegistradosHistoricos.toLocaleString('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-sub">
            Acumulado de cobros registrados desde el inicio de operaciones.
          </div>
        </article>

        <article className="metric-card ink-enter-3">
          <div className="metric-top">
            <div className="metric-label">Cobrado fiscal del mes</div>
            <span className="metric-badge">Mes actual</span>
          </div>
          <div className="metric-value">
            {totalCobradoMes.toLocaleString('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-sub">
            Pagos aplicados a documentos fiscales durante el mes actual.
          </div>
        </article>

        <article className="metric-card ink-enter-4">
          <div className="metric-top">
            <div className="metric-label">Saldo fiscal pendiente</div>
            <span className="metric-badge warn">Saldo actual</span>
          </div>
          <div className="metric-value">
            {totalPorCobrar.toLocaleString('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-sub">
            <span className="red">{clientesConDeuda} clientes</span> · {documentosConDeuda} documentos con saldo.
          </div>
        </article>

      </section>

      <section className="dashboard-grid ink-enter-5">
        <div className="dashboard-main-stack">
          <article className="panel dashboard-quote-panel">
          <div className="panel-header dashboard-quote-panel__header">
            <div>
              <span className="dashboard-section-kicker">Seguimiento comercial</span>
              <h3>Cotizaciones recientes</h3>
              <p>Las últimas cotizaciones creadas o actualizadas.</p>
            </div>
            <div className="dashboard-quote-panel__actions">
              <span className="dashboard-quote-count">{Math.min(recentDocs.length, 4)} visibles</span>
              <button type="button" className="btn" onClick={() => navigate('/cotizaciones')}>Ver cotizaciones</button>
            </div>
          </div>
          <p className="mb-2 text-xs font-semibold text-[var(--color-text-muted)] md:hidden">Desliza horizontalmente para ver todas las columnas.</p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Cliente</th>
                  <th>Fecha</th>
                  <th>Total</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {(recentDocs.length ? recentDocs.slice(0, 4) : [null]).map((doc, index) => {
                  if (!doc) {
                    return (
                      <tr key={`empty-${index}`}>
                        <td colSpan={5} style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '24px 16px' }}>
                          Aún no hay cotizaciones recientes para mostrar.
                        </td>
                      </tr>
                    );
                  }
                  const status = getStatusMeta(doc.estado);
                  return (
                    <tr key={doc.id ?? `${formatDocNumber(doc)}-${index}`} className="dashboard-quote-row">
                      <td className="dashboard-quote-document">
                        <strong>{formatDocNumber(doc)}</strong>
                      </td>
                      <td className="dashboard-quote-client">{getDocClient(doc)}</td>
                      <td>{formatShortDate(doc.fecha_emision || doc.created_at)}</td>
                      <td className="dashboard-quote-total">
                        <strong>
                          {getDocAmount(doc).toLocaleString('es-PE', { style: 'currency', currency: doc.moneda || 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </strong>
                      </td>
                      <td><span className={`status ${status.tone}`}>{status.label}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="quick-actions">
            <button type="button" className="quick-btn" onClick={() => navigate('/comprobantes/nuevo')}>
              <strong>Crear factura</strong>
              <span>Emitir comprobante a SUNAT</span>
            </button>
            <button type="button" className="quick-btn" onClick={() => navigate('/cobranza')}>
              <strong>Registrar cobro</strong>
              <span>Conciliar pago recibido</span>
            </button>
            <button type="button" className="quick-btn" onClick={() => navigate('/cobranza')}>
              <strong>Enviar recordatorio</strong>
              <span>Gestionar deuda vencida</span>
            </button>
          </div>
          </article>

          <article className="panel ink-enter-6">
            <div className="panel-header">
              <div>
                <h3>Seguimiento de cobranza</h3>
                <p>Documentos vencidos que requieren seguimiento.</p>
              </div>
            </div>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Documento</th>
                    <th>Monto</th>
                    <th>Vencimiento</th>
                    <th>Dias atraso</th>
                    <th>Estado</th>
                    <th>Accion</th>
                  </tr>
                </thead>
                <tbody>
                  {(overdueDocs.length ? overdueDocs.slice(0, 4) : [null]).map((doc, index) => {
                    if (!doc) {
                      return (
                        <tr key={`overdue-empty-${index}`}>
                          <td colSpan={7} style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '24px 16px' }}>
                            No hay documentos vencidos para mostrar.
                          </td>
                        </tr>
                      );
                    }
                    const lateDays = getDaysLate(doc);
                    const status = getStatusMeta(lateDays > 0 ? 'vencido' : 'por vencer');
                    const daysColor = lateDays ? (lateDays > 10 ? '#dc2626' : '#c76f13') : undefined;
                    return (
                      <tr key={doc.id ?? `${formatDocNumber(doc)}-due-${index}`}>
                        <td>{getDocClient(doc)}</td>
                        <td>{formatDocNumber(doc)}</td>
                        <td>{getDocAmount(doc).toLocaleString('es-PE', { style: 'currency', currency: doc.moneda || 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td>{formatShortDate(doc.fecha_vencimiento || doc.fecha_emision)}</td>
                        <td style={daysColor ? { color: daysColor, fontWeight: 800 } : undefined}>{lateDays ? `${lateDays} dias` : '-'}</td>
                        <td><span className={`status ${status.tone}`}>{status.label}</span></td>
                        <td>
                          <button type="button" className="view-btn" onClick={() => navigate('/cobranza')}>Recordar</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <aside className="side-stack">
          {urgentItems.length > 0 && (
          <article className="panel">
            <div className="panel-header">
              <div>
                <h3>Pendientes urgentes</h3>
                <p>Lista corta para operar sin perder tiempo.</p>
              </div>
            </div>
            <div className="todo-list">
              {urgentItems.map((doc, index) => {
                const lateDays = getDaysLate(doc);
                return (
                  <div key={doc.id ?? `${formatDocNumber(doc)}-${index}`} className="todo-item">
                    <div className="todo-icon">
                      {index === 0 ? <CreditCard size={18} /> : index === 1 ? <FileText size={18} /> : <Send size={18} />}
                    </div>
                    <div>
                      <strong>{formatDocNumber(doc)} · {getDocClient(doc)}</strong>
                      <span>
                        {lateDays ? `${lateDays} dias de atraso` : 'Vencimiento cercano'} · {getDocAmount(doc).toLocaleString('es-PE', { style: 'currency', currency: doc.moneda || 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                    <button type="button" className="mini-link" onClick={() => navigate('/cobranza')}>Abrir</button>
                  </div>
                );
              })}
            </div>
          </article>
          )}

          <article className="panel">
            <div className="panel-header">
              <div>
                <h3>Cuentas por cobrar</h3>
                <p>Resumen fiscal de deuda.</p>
              </div>
            </div>
            <div className="aging">
              <div className="aging-row">
                <div className="aging-top">
                  <span>Por vencer</span>
                  <strong>{porVencer.toLocaleString('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                </div>
                <div className="bar light"><i style={{ width: `${percent(porVencer, totalAging)}%` }} /></div>
              </div>
              <div className="aging-row">
                <div className="aging-top">
                  <span>Vencido</span>
                  <strong>{saldoVencido.toLocaleString('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                </div>
                <div className="bar red"><i style={{ width: `${percent(saldoVencido, totalAging)}%` }} /></div>
              </div>
            </div>
          </article>
        </aside>
      </section>
    </div>
  );
}
