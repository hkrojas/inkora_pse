import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, DollarSign } from 'lucide-react';
import { dashboard } from '../services/dashboard';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { useToast } from '../components/ui/Toast';

function agingBadge(dias) {
  const d = Number(dias || 0);
  if (d > 30) return { variant: 'ink-aging-badge--danger', label: `+${d} Días` };
  if (d > 0) return { variant: 'ink-aging-badge--warning', label: `+${d} Días` };
  if (d === 0) return { variant: 'ink-aging-badge--neutral', label: 'Vence hoy' };
  return { variant: 'ink-aging-badge--neutral', label: `Vence en ${Math.abs(d)}d` };
}

function agingDot(dias) {
  const d = Number(dias || 0);
  if (d > 30) return 'var(--color-error)';
  if (d > 0)  return 'var(--color-warning)';
  return 'var(--text-tertiary)';
}

export default function CobranzaPage() {
  const toast = useToast();
  const [vencidas, setVencidas] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([dashboard.cobranzaVencidas(), dashboard.cobranzaResumen()])
      .then(([vencidasResponse, resumenResponse]) => {
        setVencidas(Array.isArray(vencidasResponse) ? vencidasResponse : []);
        setResumen(resumenResponse);
      })
      .catch(() => toast('No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const fmt = (value) =>
    Number(value || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 });

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="page-header">
        <div className="page-header-copy">
          <p className="page-kicker">Flujo de caja</p>
          <h2 className="page-title">Cobranza</h2>
          <p className="page-subtitle">Seguimiento de saldos pendientes y vencimientos comerciales.</p>
        </div>
      </div>

      {resumen && (
        <div className="ink-metric-grid md:grid-cols-3">
          {/* Total pendiente */}
          <div className="ink-kpi-card ink-kpi-card--warning">
            <div className="ink-kpi-inner">
              <p className="ink-kpi-label">Total Pendiente</p>
              <p className="ink-kpi-value">S/ {fmt(resumen.total_por_cobrar)}</p>
              <p className="ink-kpi-note">saldo por regularizar</p>
            </div>
          </div>
          {/* Docs vencidos */}
          <div className="ink-kpi-card ink-kpi-card--danger">
            <div className="ink-kpi-inner">
              <p className="ink-kpi-label">Docs. Vencidos</p>
              <p className="ink-kpi-value">{resumen.documentos_vencidos ?? '--'}</p>
              <p className="ink-kpi-note">accion inmediata requerida</p>
            </div>
          </div>
          {/* Cobrado este mes */}
          <div className="ink-kpi-card ink-kpi-card--success">
            <div className="ink-kpi-inner">
              <p className="ink-kpi-label">Cobrado Este Mes</p>
              <p className="ink-kpi-value">S/ {fmt(resumen.total_pagado_mes)}</p>
              <p className="ink-kpi-note">monto recuperado</p>
            </div>
          </div>
        </div>
      )}

      <div className="ink-table-card">
        <div className="ink-table-header" style={{ background: 'var(--color-error-bg)' }}>
          <div className="ink-table-title">
            <AlertCircle className="h-4 w-4" style={{ color: 'var(--color-error)' }} />
            Aging Report
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
            Priorizar por días de mora.
          </span>
        </div>

        {vencidas.length === 0 ? (
          <EmptyState title="Sin vencimientos" description="No hay cotizaciones vencidas." />
        ) : (
          <table className="ink-table">
            <thead>
              <tr>
                <th>Doc.</th>
                <th>Cliente</th>
                <th>Vence</th>
                <th className="text-right">Saldo</th>
                <th className="text-center">Días</th>
                <th className="text-right" />
              </tr>
            </thead>
            <tbody>
              {vencidas.map((item) => {
                const badge = agingBadge(item.dias_vencido);
                const dot = agingDot(item.dias_vencido);
                const isOverdue = Number(item.dias_vencido || 0) > 0;
                return (
                  <tr
                    key={item.cotizacion_id}
                    style={isOverdue ? { background: 'var(--color-error-bg)' } : {}}
                  >
                    <td data-label="Doc.">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: 0, background: dot, flexShrink: 0 }} />
                        <span className="font-mono-label" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
                          {item.internal_order_number || item.document_number || `#${item.cotizacion_id}`}
                        </span>
                      </div>
                    </td>
                    <td data-label="Cliente" style={{ fontWeight: 600 }}>{item.cliente_nombre || '--'}</td>
                    <td data-label="Vence">
                      <span className="font-mono-label" style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                        {item.fecha_vencimiento
                          ? new Date(item.fecha_vencimiento).toLocaleDateString('es-PE')
                          : '--'}
                      </span>
                    </td>
                    <td data-label="Saldo" className="text-right">
                      <span className="font-mono-label" style={{ fontSize: '14px', color: isOverdue ? 'var(--color-error)' : 'var(--text-primary)' }}>
                        S/ {fmt(item.saldo_pendiente)}
                      </span>
                    </td>
                    <td data-label="Dias" className="text-center">
                      <span className={`ink-aging-badge ${badge.variant}`}>{badge.label}</span>
                    </td>
                    <td data-label="Acciones" className="text-right">
                      <div className="ink-row-actions">
                        <Link
                          to={`/cotizaciones/${item.cotizacion_id}`}
                          className="ink-row-btn"
                          title="Ver cotizacion"
                          style={{ textDecoration: 'none' }}
                        >
                          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Ver</span>
                        </Link>
                        <button
                          className="ink-row-action-pill"
                          title="Registrar pago"
                        >
                          <DollarSign className="h-3 w-3" />
                          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Pagar</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <div className="ink-table-footer">
          <span className="ink-table-count">
            <strong>{vencidas.length}</strong> registros en seguimiento
          </span>
        </div>
      </div>
    </div>
  );
}
