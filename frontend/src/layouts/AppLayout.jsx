import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AlertTriangle, Bell, Plus, Search, ShieldCheck, User, XCircle } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import { useAuth } from '../context/AuthContext';
import { FullPageSpinner } from '../components/ui/Spinner';
import PageTransition from '../components/ui/PageTransition';
import { sunat } from '../services/sunat';
import { tenant as tenantSvc } from '../services/tenant';
import { cn } from '../lib/utils/cn';

function SunatStatus() {
  const [rate, setRate] = useState(null);

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
        retryId = setTimeout(load, 60 * 1000);
      }
    };

    load();
    return () => {
      mounted = false;
      clearTimeout(retryId);
    };
  }, []);

  return (
    <div className="app-sunat-pill hidden items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2 shadow-[var(--shadow-soft)] sm:flex">
      <span className="attention-pulse-dot" />
      <span className="text-[11px] font-black uppercase tracking-[0.12em] text-[var(--color-text-muted)]">SUNAT</span>
      {rate && (
        <span className="font-mono text-[11px] font-semibold text-[var(--color-text)]">
          C {rate.buy} | V {rate.sell}
        </span>
      )}
    </div>
  );
}

const ROUTE_META = {
  '/dashboard': { title: 'Dashboard', sub: 'Centro de control diario' },
  '/clientes': { title: 'Clientes', sub: 'Relación comercial' },
  '/productos': { title: 'Productos', sub: 'Catálogo reusable' },
  '/cotizaciones': { title: 'Cotizaciones', sub: 'Motor comercial' },
  '/cobranza': { title: 'Cobranza', sub: 'Seguimiento de pagos' },
  '/guias': { title: 'Guías de remisión', sub: 'Despacho fiscal' },
  '/facturas': { title: 'Facturas', sub: 'Comprobantes tipo 01' },
  '/comprobantes/nuevo': { title: 'Crear comprobante', sub: 'Emisión central' },
  '/boletas': { title: 'Boletas', sub: 'Comprobantes tipo 03' },
  '/notas': { title: 'Notas crédito/débito', sub: 'Ajustes fiscales' },
  '/retenciones': { title: 'Retenciones', sub: 'Régimen de retenciones' },
  '/percepciones': { title: 'Percepciones', sub: 'Régimen de percepciones' },
  '/resumen-diario': { title: 'Resumen diario', sub: 'Operación diaria' },
  '/bajas': { title: 'Bajas', sub: 'Comunicación de baja' },
  '/reversiones': { title: 'Reversiones', sub: 'Corrección de documentos' },
  '/configuracion': { title: 'Configuración', sub: 'Datos del negocio' },
  '/diseno-pdf': { title: 'Diseño PDF', sub: 'Plantilla comercial' },
  '/superadmin': { title: 'Superadmin', sub: 'Control interno' },
};

function getRouteMeta(pathname) {
  if (pathname.startsWith('/cotizaciones/')) {
    return { title: 'Detalle de cotización', sub: 'Detalle comercial' };
  }
  if (pathname.startsWith('/guias/')) {
    return { title: 'Detalle de guía', sub: 'Seguimiento de despacho' };
  }
  return ROUTE_META[pathname] || { title: 'Inkora', sub: 'Operación' };
}

function SubscriptionBanner({ user }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    if (!user || user.is_superadmin) return;
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
        'flex items-center gap-3 border-b border-[var(--color-border)] px-6 py-3 text-sm font-semibold',
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
  const navigate = useNavigate();

  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;

  if (user.must_change_password && !location.pathname.startsWith('/configuracion')) {
    return <Navigate to="/configuracion?tab=seguridad" replace />;
  }

  const meta = getRouteMeta(location.pathname);
  const isSuperadmin = Boolean(user?.is_superadmin);

  const isDashboardRoute = location.pathname === '/dashboard';
  const isClientesRoute = location.pathname === '/clientes';
  const isCotizacionesRoute = location.pathname.startsWith('/cotizaciones');
  const isProductosRoute = location.pathname === '/productos';
  const isCobranzaRoute = location.pathname === '/cobranza';
  const isComprobantesNuevoRoute = location.pathname === '/comprobantes/nuevo';
  const isFacturasRoute = location.pathname === '/facturas';
  const isBoletasRoute = location.pathname === '/boletas';
  const isGuiasRoute = location.pathname.startsWith('/guias');
  const isNotasRoute = location.pathname === '/notas';
  const isResumenDiarioRoute = location.pathname === '/resumen-diario';
  const isBajasRoute = location.pathname === '/bajas';
  const isReversionesRoute = location.pathname === '/reversiones';
  const isRetencionesRoute = location.pathname === '/retenciones';
  const isPercepcionesRoute = location.pathname === '/percepciones';
  const isConfiguracionRoute = location.pathname.startsWith('/configuracion');
  const isSuperadminRoute = location.pathname === '/superadmin';

  return (
    <div
      className={cn(
        'app-dashboard-shell flex h-screen bg-[var(--color-bg)]',
        isDashboardRoute && 'app-route-dashboard',
        isClientesRoute && 'app-route-clientes',
        isCotizacionesRoute && 'app-route-cotizaciones',
        isProductosRoute && 'app-route-productos',
        isGuiasRoute && 'app-route-guias',
        isNotasRoute && 'app-route-notas',
        isResumenDiarioRoute && 'app-route-resumen-diario',
        isBajasRoute && 'app-route-bajas',
        isReversionesRoute && 'app-route-reversiones',
        isRetencionesRoute && 'app-route-retenciones',
        isPercepcionesRoute && 'app-route-percepciones',
        isConfiguracionRoute && 'app-route-configuracion',
        isSuperadminRoute && 'app-route-superadmin',
        isCobranzaRoute && 'app-route-cobranza',
        isComprobantesNuevoRoute && 'app-route-comprobantes-nuevo',
        isFacturasRoute && 'app-route-facturas',
        isBoletasRoute && 'app-route-boletas',
      )}
    >
      <Sidebar />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="app-topbar sticky top-0 z-30 grid min-h-[72px] flex-shrink-0 grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 border-b border-[var(--color-border)] bg-[rgba(255,255,255,0.94)] px-4 backdrop-blur-[18px] sm:px-6">
          <div className="flex min-w-0 flex-col pl-10 lg:pl-0">
            <div className="flex items-center gap-2.5">
              <h1 className="m-0 truncate text-[18px] font-extrabold leading-tight tracking-[-0.04em] text-[var(--color-text)]">
                {meta.title}
              </h1>
              {isSuperadmin && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-primary-soft)] px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-[var(--color-primary-text)]">
                  <ShieldCheck size={10} />
                  SA
                </span>
              )}
            </div>
            <span className="hidden text-[13px] leading-none text-[var(--color-text-muted)] sm:block">
              {meta.sub}
            </span>
          </div>

          <div className="hidden items-center gap-2.5 rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-soft)] px-4 py-2 text-[var(--color-text-soft)] sm:flex">
            <Search size={14} className="flex-shrink-0" />
            <span className="whitespace-nowrap text-[12px]">Buscar en Inkora...</span>
          </div>

          <div className="flex flex-shrink-0 items-center gap-2">
            <SunatStatus />

            <button
              type="button"
              className="relative inline-flex h-[42px] w-[42px] items-center justify-center rounded-[13px] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] shadow-[var(--shadow-soft)] transition-colors hover:text-[var(--color-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2"
              aria-label="Ver notificaciones"
              title="Notificaciones"
            >
              <Bell size={15} />
              <span className="absolute right-[10px] top-[10px] h-[6px] w-[6px] rounded-full border border-white bg-[var(--color-primary)]" />
            </button>

            <button
              type="button"
              className="inline-flex h-[42px] w-[42px] items-center justify-center rounded-[13px] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] shadow-[var(--shadow-soft)] transition-colors hover:text-[var(--color-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2"
              aria-label="Abrir menú de usuario"
              title="Usuario"
            >
              <User size={15} />
            </button>

            <button
              className="hidden items-center gap-2 rounded-[18px] bg-[var(--color-dark-btn)] px-6 py-3 text-[16px] font-extrabold text-white transition-opacity hover:opacity-90 sm:flex"
              type="button"
              onClick={() => navigate('/comprobantes/nuevo')}
              aria-label="Crear comprobante"
            >
              Crear comprobante
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/15">
                <Plus size={11} strokeWidth={2.5} />
              </span>
            </button>
          </div>
        </header>

        <SubscriptionBanner user={user} />

        <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 sm:py-7">
          <PageTransition>
            <Outlet />
          </PageTransition>
        </main>
      </div>
    </div>
  );
}
