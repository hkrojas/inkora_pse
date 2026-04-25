import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { AlertTriangle, ShieldCheck, XCircle, TrendingUp } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import { useAuth } from '../context/AuthContext';
import { FullPageSpinner } from '../components/ui/Spinner';
import { sunat } from '../services/sunat';
import { tenant as tenantSvc } from '../services/tenant';
import { cn } from '../lib/utils/cn';

function SunatExchangeRate() {
  const [rate, setRate] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    let retryId;

    const load = async () => {
      try {
        const data = await sunat.exchangeRate();
        if (!mounted) return;
        setRate(data);
        retryId = setTimeout(load, 30 * 60 * 1000);
      } catch {
        if (!mounted) return;
        setRate(null);
        retryId = setTimeout(load, 60 * 1000);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    return () => {
      mounted = false;
      clearTimeout(retryId);
    };
  }, []);

  const baseClass =
    'inline-flex items-center gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-soft)] px-3 py-1.5 text-xs font-bold text-[var(--color-text)]';

  if (loading) {
    return (
      <span className={cn(baseClass, 'opacity-60')}>
        <TrendingUp size={13} className="text-[var(--color-text-muted)]" />
        <span className="text-[var(--color-text-muted)]">TC</span>
        <span className="font-mono">...</span>
      </span>
    );
  }

  if (!rate) {
    return (
      <span className={cn(baseClass, 'opacity-70')}>
        <TrendingUp size={13} className="text-[var(--color-text-muted)]" />
        <span className="text-[var(--color-text-muted)]">TC</span>
        <span className="font-mono">N/D</span>
      </span>
    );
  }

  return (
    <span
      className={cn(baseClass, rate.stale && 'opacity-70')}
      title={`SUNAT ${rate.date}`}
    >
      <TrendingUp size={13} className="text-[var(--color-primary)]" />
      <span className="text-[var(--color-text-muted)]">TC SUNAT</span>
      <span className="font-mono">
        C {rate.buy} <span className="text-[var(--color-text-soft)]">|</span> V {rate.sell}
      </span>
    </span>
  );
}

function SystemClock() {
  const [time, setTime] = useState('');
  const [date, setDate] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const h = String(now.getHours()).padStart(2, '0');
      const m = String(now.getMinutes()).padStart(2, '0');
      setTime(`${h}:${m}`);
      setDate(
        now
          .toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric' })
          .toUpperCase(),
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="hidden flex-col items-end leading-tight sm:flex">
      <span className="font-mono text-sm font-bold text-[var(--color-text)]">{time}</span>
      <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-text-soft)]">
        {date}
      </span>
    </div>
  );
}

const ROUTE_META = {
  '/dashboard': { kicker: 'Resumen operativo', title: 'Panel Inkora', breadcrumb: 'Inicio / Dashboard' },
  '/clientes': { kicker: 'Relación comercial', title: 'Clientes', breadcrumb: 'Catálogo / Clientes' },
  '/productos': { kicker: 'Catálogo reusable', title: 'Productos', breadcrumb: 'Catálogo / Productos' },
  '/cotizaciones': { kicker: 'Motor comercial', title: 'Cotizaciones', breadcrumb: 'Ventas / Cotizaciones' },
  '/cobranza': { kicker: 'Flujo de caja', title: 'Cobranza', breadcrumb: 'Ventas / Cobranza' },
  '/guias': { kicker: 'Despacho fiscal', title: 'Guías de remisión', breadcrumb: 'Logística / Guías' },
  '/facturas': { kicker: 'Comprobantes tipo 01', title: 'Facturas', breadcrumb: 'Ventas / Facturas' },
  '/comprobantes/nuevo': { kicker: 'Emisión central', title: 'Crear comprobante', breadcrumb: 'Ventas / Emisión' },
  '/boletas': { kicker: 'Comprobantes tipo 03', title: 'Boletas', breadcrumb: 'Ventas / Boletas' },
  '/notas': { kicker: 'Ajustes fiscales', title: 'Notas Crédito/Débito', breadcrumb: 'Ventas / Notas' },
  '/retenciones': { kicker: 'Régimen de retenciones', title: 'Retenciones', breadcrumb: 'SUNAT / Retenciones' },
  '/percepciones': { kicker: 'Régimen de percepciones', title: 'Percepciones', breadcrumb: 'SUNAT / Percepciones' },
  '/resumen-diario': { kicker: 'Consolidado de boletas', title: 'Resumen Diario', breadcrumb: 'SUNAT / Resumen Diario' },
  '/bajas': { kicker: 'Anulación ante SUNAT', title: 'Comunicación de Bajas', breadcrumb: 'SUNAT / Bajas' },
  '/reversiones': { kicker: 'Reversión de documentos', title: 'Reversiones', breadcrumb: 'SUNAT / Reversiones' },
  '/configuracion': { kicker: 'Datos del negocio', title: 'Perfil de empresa', breadcrumb: 'Sistema / Perfil' },
  '/cambiar-password': { kicker: 'Seguridad de cuenta', title: 'Cambiar contraseña', breadcrumb: 'Sistema / Contraseña' },
  '/diseno-pdf': { kicker: 'Plantilla comercial', title: 'Diseño PDF', breadcrumb: 'Sistema / Diseño PDF' },
  '/superadmin': { kicker: 'Control interno', title: 'Superadmin', breadcrumb: 'Sistema / Superadmin' },
};

function getRouteMeta(pathname) {
  if (pathname.startsWith('/cotizaciones/')) {
    return { kicker: 'Detalle comercial', title: 'Detalle de cotización', breadcrumb: 'Ventas / Cotizaciones / Detalle' };
  }
  if (pathname.startsWith('/guias/')) {
    return { kicker: 'Seguimiento de despacho', title: 'Detalle de guía', breadcrumb: 'Logística / Guías / Detalle' };
  }
  return ROUTE_META[pathname] || { kicker: 'Operación', title: 'Inkora', breadcrumb: 'Inkora' };
}

function SubscriptionBanner({ user }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    if (!user || user.is_superadmin || user.rol === 'superadmin') return;
    tenantSvc
      .subscriptionStatus()
      .then((data) => {
        if (data.message) setStatus(data);
      })
      .catch(() => {});
  }, [user]);

  if (!status) return null;

  const isBlocked = status.emission_blocked;
  const Icon = isBlocked ? XCircle : AlertTriangle;

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-6 py-2.5 text-sm font-semibold border-b border-[var(--color-border)]',
        isBlocked
          ? 'bg-[var(--color-danger-soft)] text-[var(--color-danger-text)]'
          : 'bg-[var(--color-warning-soft)] text-[var(--color-warning-text)]',
      )}
    >
      <Icon size={16} className="flex-shrink-0" />
      <span>{status.message}</span>
    </div>
  );
}

export default function AppLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;

  if (user.must_change_password && location.pathname !== '/cambiar-password') {
    return <Navigate to="/cambiar-password" replace />;
  }

  const meta = getRouteMeta(location.pathname);
  const isSuperadmin = user?.is_superadmin || user?.rol === 'superadmin';

  return (
    <>
      {/* Línea de tensión decorativa (gradient marca) */}
      <div
        className="fixed inset-x-0 top-0 z-[100] h-[3px]"
        style={{
          background: 'linear-gradient(90deg, #2563EB 0%, #7C3AED 60%, #D946EF 100%)',
        }}
        aria-hidden="true"
      />

      <div className="flex min-h-screen bg-[var(--color-bg)]">
        <Sidebar />

        <div className="flex min-w-0 flex-1 flex-col">
          {/* Topbar */}
          <header className="sticky top-0 z-30 flex flex-col gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6 sm:py-4">
            {/* Lado izquierdo: breadcrumb + título */}
            <div className="flex flex-col gap-0.5 pl-12 lg:pl-0">
              <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--color-text-soft)]">
                {meta.breadcrumb}
              </span>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-extrabold tracking-tight text-[var(--color-text)] sm:text-xl">
                  {meta.title}
                </h1>
                {isSuperadmin && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-purple-soft)] px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-purple-text)]">
                    <ShieldCheck size={10} />
                    superadmin
                  </span>
                )}
              </div>
              <p className="text-xs text-[var(--color-text-muted)]">{meta.kicker}</p>
            </div>

            {/* Lado derecho: chips de operación */}
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <SunatExchangeRate />
              <SystemClock />
              <div className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--color-success-soft)] px-2.5 py-1.5 text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-success-text)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]" />
                SUNAT
              </div>
            </div>
          </header>

          <SubscriptionBanner user={user} />

          {/* Contenido */}
          <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
            <Outlet />
          </main>
        </div>
      </div>
    </>
  );
}
