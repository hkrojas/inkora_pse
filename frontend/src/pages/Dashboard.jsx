import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowUpRight, Minus, Bell, CreditCard } from 'lucide-react';
import { dashboard } from '../services/dashboard';
import Spinner from '../components/ui/Spinner';
import Badge, { statusBadge } from '../components/ui/Badge';
import { useAuth } from '../context/AuthContext';

/* ── KPI Card ──────────────────────────────────────────────── */
function KpiCard({ label, value, note, noteUp, variant = 'brand', sparkline }) {
  const noteClass = noteUp === true
    ? 'ink-kpi-note ink-kpi-note--up'
    : noteUp === false
      ? 'ink-kpi-note ink-kpi-note--warn'
      : 'ink-kpi-note';

  return (
    <div className={`ink-kpi-card ink-kpi-card--${variant}`}>
      <div className="ink-kpi-inner">
        <p className="ink-kpi-label">{label}</p>
        <p className="ink-kpi-value">{value ?? '--'}</p>
        {note && (
          <p className={noteClass}>
            {noteUp === true && <ArrowUpRight className="h-3 w-3" />}
            {noteUp === false && <Minus className="h-3 w-3" />}
            {note}
          </p>
        )}
      </div>
      {sparkline && (
        <svg
          className="ink-kpi-sparkline"
          viewBox="0 0 100 50"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path d={sparkline.line} stroke="currentColor" strokeWidth="2.5" fill="none" />
          {sparkline.fill && <path d={sparkline.fill} fill="currentColor" />}
        </svg>
      )}
    </div>
  );
}

/* ── Cobranza vencida row ──────────────────────────────────── */
function VencidaRow({ item }) {
  const saldo = Number(item.saldo_pendiente || 0);
  const fecha = item.fecha_vencimiento
    ? new Date(item.fecha_vencimiento).toLocaleDateString('es-PE')
    : '--';

  return (
    <div className="ink-vencida-row">
      <div className="ink-vencida-id">
        {(item.cliente_nombre || 'C')[0].toUpperCase()}
      </div>
      <div className="ink-vencida-info">
        <p className="ink-vencida-name">{item.cliente_nombre || '--'}</p>
        <div className="ink-vencida-meta">
          <Badge variant={statusBadge(item.payment_status)}>
            {item.payment_status || 'pendiente'}
          </Badge>
          <span className="ink-vencida-date">
            Venció: {fecha}
          </span>
        </div>
      </div>
      <div className="ink-vencida-amount">
        <p className="ink-vencida-saldo">
          S/ {saldo.toLocaleString('es-PE', { minimumFractionDigits: 2 })}
        </p>
      </div>
      <div className="ink-vencida-action">
        <Link to="/cobranza" className="btn-primary">
          <Bell className="h-3 w-3" />
          Notificar
        </Link>
      </div>
    </div>
  );
}

/* ── Dashboard ─────────────────────────────────────────────── */
export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [vencidas, setVencidas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      dashboard.stats().catch(() => null),
      dashboard.cobranzaVencidas().catch(() => []),
    ])
      .then(([s, v]) => {
        setStats(s);
        setVencidas(Array.isArray(v) ? v.slice(0, 5) : []);
      })
      .catch(() => setError('No se pudo cargar el dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const ingresos = stats?.ingresos_totales != null
    ? `S/ ${Number(stats.ingresos_totales).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`
    : '--';

  const porCobrar = stats?.saldos_por_cobrar != null
    ? `S/ ${Number(stats.saldos_por_cobrar).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`
    : '--';

  return (
    <div className="page-shell">
      <div className="page-header">
        <div className="page-header-copy">
          <p className="page-kicker">Centro de mando</p>
          <h2 className="page-title">
            Hola, {user?.nombre_completo?.split(' ')[0] || 'bienvenido'}
          </h2>
          <p className="page-subtitle">
            Resumen de liquidez y flujo fiscal del período actual.
          </p>
        </div>
        <div className="page-actions">
          <Link to="/cotizaciones" className="btn-primary" style={{ gap: '8px' }}>
            Nueva cotizacion →
          </Link>
        </div>
      </div>

      {error && (
        <div className="ink-inline-alert ink-inline-alert-error">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Grid */}
      <div className="ink-metric-grid lg:grid-cols-4 md:grid-cols-2">
        <KpiCard
          variant="brand"
          label="Emisiones (Mes)"
          value={stats?.documentos_emitidos_mes ?? '--'}
          note="documentos fiscales"
          sparkline={{
            line: 'M0 50 L20 38 L40 42 L60 18 L80 28 L100 8',
            fill: 'M0 50 L20 38 L40 42 L60 18 L80 28 L100 8 L100 50 L0 50 Z',
          }}
        />
        <KpiCard
          variant="success"
          label="Ingresos Cobrados"
          value={ingresos}
          note="+cobrado este período"
          noteUp={true}
          sparkline={{
            line: 'M0 50 L20 34 L40 38 L60 14 L80 20 L100 4',
            fill: 'M0 50 L20 34 L40 38 L60 14 L80 20 L100 4 L100 50 L0 50 Z',
          }}
        />
        <KpiCard
          variant="warning"
          label="Capital Por Cobrar"
          value={porCobrar}
          note="saldo pendiente"
          noteUp={false}
          sparkline={{
            line: 'M0 50 L20 25 L40 25 L60 25 L80 25 L100 25',
          }}
        />
        <KpiCard
          variant="danger"
          label="Docs. Vencidos"
          value={stats?.documentos_vencidos ?? '--'}
          note="acción inmediata requerida"
        />
      </div>

      {/* Cobranza vencida */}
      {vencidas.length > 0 && (
        <div className="ink-table-card">
          <div className="ink-table-header">
            <div className="ink-table-title">
              <CreditCard className="h-4 w-4" style={{ color: 'var(--color-warning)' }} />
              Ledger: Cobranza Urgente
            </div>
            <Link to="/cobranza" className="btn-secondary">
              Ver todo →
            </Link>
          </div>
          <div>
            {vencidas.map((item) => (
              <VencidaRow key={item.cotizacion_id} item={item} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
