import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Clock,
  CreditCard,
  DollarSign,
  FileText,
  Package,
  Receipt,
  TrendingUp,
  UserPlus,
  Users,
} from 'lucide-react';
import { dashboard } from '../services/dashboard';
import Spinner from '../components/ui/Spinner';
import { useAuth } from '../context/AuthContext';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';

/* ── Helpers ─────────────────────────────────────────────── */

function formatCurrency(value, moneda = 'PEN') {
  if (value == null) return '--';
  const symbol = moneda === 'USD' ? '$' : 'S/';
  return `${symbol} ${Number(value).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`;
}

function formatDate(date) {
  if (!date) return '--';
  return new Date(date).toLocaleDateString('es-PE');
}

function mapEstado(variant) {
  const map = {
    pagada: 'paid',
    paid: 'paid',
    aceptado: 'sent',
    enviado: 'sent',
    sent: 'sent',
    pendiente: 'partial',
    partial: 'partial',
    parcial: 'partial',
    vencida: 'overdue',
    overdue: 'overdue',
    anulado: 'cancelled',
    cancelled: 'cancelled',
    cancelada: 'cancelled',
  };
  return map[variant?.toLowerCase()] || 'draft';
}

function tipoComprobanteLabel(tipo) {
  const map = {
    '01': 'Factura',
    '03': 'Boleta',
    '07': 'Nota de crédito',
    '08': 'Nota de débito',
    '09': 'Guía de remisión',
    '20': 'Retención',
    '40': 'Percepción',
  };
  return map[tipo] || tipo || 'Comprobante';
}

/* ── Subcomponents ───────────────────────────────────────── */

function KpiCard({ label, value, note, icon: Icon }) {
  return (
    <Card className="flex flex-col justify-between gap-3">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-soft)]">
          {label}
        </span>
        {Icon && <Icon size={18} className="text-[var(--color-text-muted)]" />}
      </div>
      <div>
        <div className="text-2xl font-extrabold tracking-tight text-[var(--color-text)]">
          {value ?? '--'}
        </div>
        {note && (
          <div className="mt-1 text-xs font-medium text-[var(--color-text-muted)]">
            {note}
          </div>
        )}
      </div>
    </Card>
  );
}

function DocumentRow({ doc }) {
  const num =
    doc.serie && doc.correlativo
      ? `${doc.serie}-${String(doc.correlativo).padStart(4, '0')}`
      : '--';
  const cliente = doc.cliente?.razon_social || doc.cliente?.nombre || '--';
  const docLabel = tipoComprobanteLabel(doc.tipo_comprobante);

  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-soft)] p-4">
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-[var(--color-text)]">
            {num}
          </span>
          <span className="text-xs font-medium text-[var(--color-text-muted)]">
            {docLabel}
          </span>
        </div>
        <span className="truncate text-sm font-semibold text-[var(--color-text)]">
          {cliente}
        </span>
        <span className="text-xs text-[var(--color-text-soft)]">
          {formatDate(doc.fecha_emision)} · {doc.cliente?.numero_documento || '--'}
        </span>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="font-mono text-sm font-bold text-[var(--color-text)]">
          {formatCurrency(doc.total_venta, doc.moneda)}
        </span>
        <Badge variant={mapEstado(doc.estado)}>
          {doc.estado || 'Borrador'}
        </Badge>
      </div>
    </div>
  );
}

function OverdueRow({ doc }) {
  const num =
    doc.serie && doc.correlativo
      ? `${doc.serie}-${String(doc.correlativo).padStart(4, '0')}`
      : '--';
  const cliente = doc.cliente?.razon_social || doc.cliente?.nombre || '--';

  return (
    <div className="flex items-center justify-between gap-4 border-b border-[var(--color-border)] py-3 last:border-b-0">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="truncate text-sm font-semibold text-[var(--color-text)]">
          {cliente}
        </span>
        <span className="font-mono text-xs text-[var(--color-text-muted)]">
          {num} · {doc.cliente?.numero_documento || '--'}
        </span>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="font-mono text-sm font-bold text-[var(--color-danger)]">
          {formatCurrency(doc.total_venta, doc.moneda)}
        </span>
        <span className="text-xs text-[var(--color-text-soft)]">
          Venció: {formatDate(doc.fecha_emision)}
        </span>
      </div>
    </div>
  );
}

/* ── Dashboard ───────────────────────────────────────────── */
export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [recentDocs, setRecentDocs] = useState([]);
  const [overdue, setOverdue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      dashboard.stats().catch(() => null),
      dashboard.recentDocuments().catch(() => []),
      dashboard.pendingInvoices().catch(() => []),
    ])
      .then(([s, r, p]) => {
        setStats(s);
        setRecentDocs(Array.isArray(r) ? r.slice(0, 6) : []);
        setOverdue(Array.isArray(p) ? p.slice(0, 6) : []);
      })
      .catch(() =>
        setError('No se pudo cargar el dashboard. Revisa tu conexión e inténtalo nuevamente.')
      )
      .finally(() => setLoading(false));
  }, []);

  const fechaHoy = new Date().toLocaleDateString('es-PE', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const kpis = [
    {
      label: 'Ventas del mes',
      value: formatCurrency(stats?.ventas_mes),
      note: 'Ingresos acumulados',
      icon: TrendingUp,
    },
    {
      label: 'Por cobrar',
      value: formatCurrency(stats?.por_cobrar),
      note: 'Saldo pendiente',
      icon: CreditCard,
    },
    {
      label: 'Facturas vencidas',
      value: stats?.facturas_vencidas ?? '--',
      note: 'Documentos vencidos',
      icon: AlertCircle,
    },
    {
      label: 'Cotizaciones aprobadas',
      value: stats?.cotizaciones_aprobadas ?? '--',
      note: 'Este mes',
      icon: FileText,
    },
    {
      label: 'Clientes activos',
      value: stats?.clientes_activos ?? '--',
      note: 'Registrados',
      icon: Users,
    },
    {
      label: 'Productos registrados',
      value: stats?.productos_registrados ?? '--',
      note: 'En catálogo',
      icon: Package,
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-extrabold tracking-tight text-[var(--color-text)]">
            Dashboard
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Tu negocio al día. Revisa tus ventas, comprobantes pendientes y pagos recibidos en un
            solo lugar.
          </p>
          <p className="text-xs font-medium text-[var(--color-text-soft)] capitalize">
            {fechaHoy}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => navigate('/comprobantes/nuevo')}>
            <Receipt size={16} />
            Nueva factura
          </Button>
          <Button size="sm" variant="secondary" onClick={() => navigate('/cotizaciones')}>
            <FileText size={16} />
            Nueva cotización
          </Button>
          <Button size="sm" variant="secondary" onClick={() => navigate('/cobranza')}>
            <DollarSign size={16} />
            Registrar pago
          </Button>
          <Button size="sm" variant="secondary" onClick={() => navigate('/clientes')}>
            <UserPlus size={16} />
            Crear cliente
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-2xl border border-[var(--color-danger-soft)] bg-[var(--color-danger-soft)] p-4 text-sm text-[var(--color-danger-text)]">
          <AlertCircle size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {kpis.map((kpi) => (
          <KpiCard key={kpi.label} {...kpi} />
        ))}
      </div>

      {/* Chart + Pending actions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text)]">
              Tendencia de ventas
            </h2>
            <span className="text-xs text-[var(--color-text-muted)]">Últimos 30 días</span>
          </div>
          <div className="flex h-64 items-center justify-center rounded-2xl bg-[var(--color-surface-muted)]">
            <BarChart3 size={32} className="text-[var(--color-text-soft)]" />
            <span className="ml-2 text-sm font-medium text-[var(--color-text-muted)]">
              Gráfico próximamente
            </span>
          </div>
        </Card>

        <Card className="flex flex-col gap-4">
          <h2 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text)]">
            Acciones pendientes
          </h2>
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3 rounded-xl bg-[var(--color-warning-soft)] p-3">
              <Clock size={18} className="shrink-0 text-[var(--color-warning)]" />
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-[var(--color-warning-text)]">
                  Enviar comprobantes a SUNAT
                </span>
                <span className="text-xs text-[var(--color-warning-text)] opacity-80">
                  {recentDocs.filter((d) => !d.sunat_xml_url).length} pendientes
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-[var(--color-primary-soft)] p-3">
              <CheckCircle2 size={18} className="shrink-0 text-[var(--color-primary)]" />
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-[var(--color-primary)]">
                  Confirmar pagos recibidos
                </span>
                <span className="text-xs text-[var(--color-primary)] opacity-80">
                  Revisa la bandeja de cobranza
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-[var(--color-danger-soft)] p-3">
              <AlertTriangle size={18} className="shrink-0 text-[var(--color-danger)]" />
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-[var(--color-danger-text)]">
                  Cobrar facturas vencidas
                </span>
                <span className="text-xs text-[var(--color-danger-text)] opacity-80">
                  {overdue.length > 0 ? `${overdue.length} por cobrar` : 'Ninguna pendiente'}
                </span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Latest documents + Fiscal status */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text)]">
              Últimos comprobantes
            </h2>
            <Link
              to="/facturas"
              className="inline-flex items-center gap-1 text-xs font-bold text-[var(--color-primary)] hover:underline"
            >
              Ver todo
              <ArrowUpRight size={14} />
            </Link>
          </div>
          <div className="flex flex-col gap-3">
            {recentDocs.length > 0 ? (
              recentDocs.map((doc) => <DocumentRow key={doc.id} doc={doc} />)
            ) : (
              <div className="flex flex-col items-center gap-3 py-10">
                <CheckCircle2 size={24} className="text-[var(--color-success)]" />
                <p className="text-sm font-semibold text-[var(--color-text)]">
                  Sin comprobantes recientes
                </p>
                <p className="text-center text-xs text-[var(--color-text-muted)]">
                  No se encontraron documentos emitidos recientemente.
                </p>
              </div>
            )}
          </div>
        </Card>

        <Card className="flex flex-col gap-4">
          <h2 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text)]">
            Estado fiscal
          </h2>
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-success-soft)]">
                <CheckCircle2 size={20} className="text-[var(--color-success)]" />
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-[var(--color-text)]">
                  Conectado a SUNAT
                </span>
                <span className="text-xs text-[var(--color-text-muted)]">Emisión activa</span>
              </div>
            </div>
            <div className="rounded-xl bg-[var(--color-surface-muted)] p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[var(--color-text-muted)]">
                  Comprobantes emitidos (mes)
                </span>
                <span className="font-mono font-bold text-[var(--color-text)]">
                  {stats?.documentos_emitidos_mes ?? '--'}
                </span>
              </div>
            </div>
            <div className="rounded-xl bg-[var(--color-surface-muted)] p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[var(--color-text-muted)]">Ambiente</span>
                <Badge variant="paid">Beta</Badge>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Overdue invoices */}
      <Card className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text)]">
            Facturas vencidas
          </h2>
          <Link
            to="/cobranza"
            className="inline-flex items-center gap-1 text-xs font-bold text-[var(--color-primary)] hover:underline"
          >
            Ver cobranza
            <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="flex flex-col">
          {overdue.length > 0 ? (
            overdue.map((doc) => <OverdueRow key={doc.id} doc={doc} />)
          ) : (
            <div className="flex flex-col items-center gap-3 py-10">
              <TrendingUp size={24} className="text-[var(--color-success)]" />
              <p className="text-sm font-semibold text-[var(--color-text)]">Todo al día</p>
              <p className="text-center text-xs text-[var(--color-text-muted)]">
                No hay facturas vencidas. Sigue así.
              </p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
