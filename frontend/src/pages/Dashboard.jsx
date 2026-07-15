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

function getDocTypeLabel(doc) {
  const kind = doc?.document_kind || doc?.tipo_comprobante;
  if (kind === 'quotation' || kind === '00') return 'COT.';
  if (kind === 'invoice' || kind === '01') return 'FACTURA';
  if (kind === 'receipt' || kind === '03') return 'BOLETA';
  if (kind === 'debit_note' || kind === '08') return 'ND';
  if (kind === 'credit_note' || kind === '07') return 'NC';
  if (kind === 'guide' || kind === '09') return 'GUÍA';
  return 'DOC';
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

  const ingresosTotales = safeNumber(stats?.ingresos_totales);
  const totalCobradoMes = safeNumber(cobranza?.total_pagado_mes);
  const totalPorCobrar = safeNumber(cobranza?.total_por_cobrar ?? stats?.saldos_por_cobrar);
  const saldoVencido = safeNumber(cobranza?.total_vencido ?? stats?.saldo_vencido);
  const documentosPendientes = safeNumber(cobranza?.documentos_pendientes);
  const clientesConDeuda = safeNumber(cobranza?.clientes_con_deuda ?? overdueDocs.length);
  const docsRechazados = [...recentDocs, ...overdueDocs].filter(
    (doc) => getStatusMeta(doc?.estado).tone === 'bad',
  ).length;
  const cotizacionesPendientes = recentDocs.filter(
    (doc) => doc?.document_kind === 'quotation' && getStatusMeta(doc?.estado).tone !== 'ok',
  ).length;

  const porVencer = Math.max(totalPorCobrar - saldoVencido, 0);
  const vencidoCorto = Math.min(saldoVencido, totalPorCobrar * 0.72);
  const vencidoLargo = Math.max(0, saldoVencido - vencidoCorto);
  const totalAging = Math.max(totalPorCobrar, 1);

  const attentionCards = [
    {
      value: documentosPendientes,
      label: 'Documentos fiscales por cobrar, no vencidos.',
      action: 'Revisar ahora',
      href: '/cobranza',
    },
    {
      value: docsRechazados,
      label: 'Alertas en documentos recientes.',
      action: 'Ver documentos',
      href: '/facturas',
    },
    {
      value: clientesConDeuda,
      label: 'Clientes con deuda fiscal.',
      action: 'Ver cobranzas',
      href: '/cobranza',
    },
    {
      value: cotizacionesPendientes,
      label: 'Cotizaciones recientes pendientes.',
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
        description="Lo importante no es ver gráficos: es saber qué cobrar, qué emitir y qué corregir hoy."
        meta={<span className="operational-page-header__scope">Vista consolidada del negocio</span>}
        actions={
          <button type="button" className="btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '9px' }}>
            <CalendarDays size={16} />
            {formatDashboardMonth()}
          </button>
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

      <section className="attention ink-enter-2">
        <div className="attention-title">
          <span className="attention-title-badge">
            <CircleAlert size={16} />
          </span>
          <h3>Necesita atención hoy</h3>
          <p>Prioriza pendientes que afectan caja, emisión fiscal o seguimiento comercial.</p>
        </div>
        {actionableAttentionCards.map((item) => (
          <div
            key={item.label}
            className="attention-card"
            onClick={() => navigate(item.href)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && navigate(item.href)}
          >
            <strong>{item.value}</strong>
            <span className="attention-card-text">{item.label}</span>
            <div className="attention-card-link">
              {item.action}
              <ArrowRight size={13} />
            </div>
          </div>
        ))}
        {actionableAttentionCards.length === 0 && (
          <div className="attention-card attention-card--calm">
            <strong>Todo al día</strong>
            <span className="attention-card-text">No hay alertas comerciales o fiscales que requieran una acción inmediata.</span>
          </div>
        )}
      </section>

      <section className="metrics-grid">
        <article className="metric-card ink-enter-3">
          <div className="metric-top">
            <div className="metric-label">Pagos fiscales registrados</div>
            <span className="metric-badge neutral">Historico</span>
          </div>
          <div className="metric-value">
            {ingresosTotales.toLocaleString('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="metric-sub">
            Acumulado histórico de pagos aplicados a documentos fiscales.
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
            Equivale al <strong>{percent(totalCobradoMes, ingresosTotales || 1)}%</strong> del acumulado histórico.
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
            <span className="red">{clientesConDeuda} clientes</span> · {overdueDocs.length || documentosPendientes} documentos.
          </div>
        </article>

        <article className={`metric-card ink-enter-4${docsRechazados === 0 ? ' metric-card--quiet' : ''}`}>
          <div className="metric-top">
          <div className="metric-label">Alertas documentales visibles</div>
            <span className={`metric-badge ${docsRechazados > 0 ? 'warn' : ''}`}>
              {docsRechazados > 0 ? 'Revisar' : 'Sin alertas'}
            </span>
          </div>
          <div className="metric-value">{docsRechazados === 0 ? '—' : docsRechazados}</div>
          <div className="metric-sub">
            {docsRechazados > 0
              ? 'Documentos con alerta en los listados recientes.'
              : 'Sin alertas en los documentos visibles del dashboard.'}
          </div>
        </article>
      </section>

      <section className="dashboard-grid ink-enter-5">
        <div className="dashboard-main-stack">
          <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Actividad reciente</h3>
              <p>Ultimos comprobantes, pagos y acciones importantes.</p>
            </div>
            <button type="button" className="btn" onClick={() => navigate('/facturas')}>Ver todo</button>
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
                          Aun no hay actividad reciente para mostrar.
                        </td>
                      </tr>
                    );
                  }
                  const status = getStatusMeta(doc.estado);
                  return (
                    <tr key={doc.id ?? `${formatDocNumber(doc)}-${index}`}>
                      <td>
                        <strong>{formatDocNumber(doc)}</strong>
                        <span className="status neutral" style={{ marginLeft: '8px', fontSize: '10px', padding: '2px 6px' }}>
                          {getDocTypeLabel(doc)}
                        </span>
                      </td>
                      <td>{getDocClient(doc)}</td>
                      <td>{formatShortDate(doc.fecha_emision || doc.created_at)}</td>
                      <td>
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
            <button type="button" className="quick-btn" onClick={() => navigate('/cotizaciones')}>
              <strong>Enviar recordatorio</strong>
              <span>Gestionar deuda vencida</span>
            </button>
          </div>
          </article>

          <article className="panel ink-enter-6">
            <div className="panel-header">
              <div>
                <h3>Seguimiento de cobranza</h3>
                <p>Clientes con documentos por vencer o vencidos.</p>
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
          <article className="panel">
            <div className="panel-header">
              <div>
                <h3>Pendientes urgentes</h3>
                <p>Lista corta para operar sin perder tiempo.</p>
              </div>
            </div>
            <div className="todo-list">
              {urgentItems.length > 0 ? urgentItems.map((doc, index) => {
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
              }) : (
                <div className="todo-item">
                  <div className="todo-icon"><CircleAlert size={18} /></div>
                  <div>
                    <strong>No hay pendientes urgentes para mostrar.</strong>
                    <span>Cuando existan documentos vencidos, rechazos fiscales o acciones criticas, apareceran aqui.</span>
                  </div>
                </div>
              )}
            </div>
          </article>

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
                  <span>Vencido - tramo visual</span>
                  <strong>{vencidoCorto.toLocaleString('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                </div>
                <div className="bar orange"><i style={{ width: `${percent(vencidoCorto, totalAging)}%` }} /></div>
              </div>
              <div className="aging-row">
                <div className="aging-top">
                  <span>Vencido - resto visual</span>
                  <strong>{vencidoLargo.toLocaleString('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                </div>
                <div className="bar red"><i style={{ width: `${percent(vencidoLargo, totalAging)}%` }} /></div>
              </div>
            </div>
          </article>
        </aside>
      </section>
    </div>
  );
}
