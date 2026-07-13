import { useEffect, useMemo, useRef, useState } from 'react';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  CreditCard,
  FileText,
  LayoutDashboard,
  LogOut,
  Package,
  Plus,
  Receipt,
  Search,
  Settings,
  ShieldCheck,
  Truck,
  User,
  Users,
  XCircle,
} from 'lucide-react';
import Sidebar from '../components/Sidebar';
import { useAuth } from '../context/AuthContext';
import { FullPageSpinner } from '../components/ui/Spinner';
import PageTransition from '../components/ui/PageTransition';
import { sunat } from '../services/sunat';
import { tenant as tenantSvc } from '../services/tenant';
import { cn } from '../lib/utils/cn';

function SunatStatus() {
  const [rate, setRate] = useState(null);
  const rateDetail = rate
    ? `Tipo de cambio SUNAT: compra ${rate.buy}, venta ${rate.sell}.`
    : 'Actualizando el tipo de cambio SUNAT.';

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
    <div
      className="app-sunat-pill hidden items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2 shadow-[var(--shadow-soft)] sm:flex"
      role="status"
      aria-live="polite"
      aria-label={rateDetail}
      title={rateDetail}
    >
      <span className="attention-pulse-dot" />
      <span className="text-[11px] font-black uppercase tracking-[0.12em] text-[var(--color-text-muted)]">SUNAT</span>
      <span className="hidden text-[11px] font-semibold text-[var(--color-text-soft)] xl:inline">Tipo de cambio</span>
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

const SEARCH_MODULES = [
  { label: 'Dashboard', path: '/dashboard', hint: 'Resumen operativo diario', icon: LayoutDashboard, keywords: 'inicio resumen centro operativo dashboard alertas' },
  { label: 'Clientes', path: '/clientes', hint: 'Buscar por razon social, RUC, DNI o telefono', icon: Users, keywords: 'cliente clientes ruc dni documento contacto empresa' },
  { label: 'Cotizaciones', path: '/cotizaciones', hint: 'Historial comercial y PDFs de cotizacion', icon: FileText, keywords: 'cotizacion cotizaciones orden presupuesto propuesta historial' },
  { label: 'Productos', path: '/productos', hint: 'Catalogo, codigos y precios', icon: Package, keywords: 'producto productos servicio sku codigo catalogo precio' },
  { label: 'Cobranza', path: '/cobranza', hint: 'Saldos, vencimientos y seguimiento', icon: CreditCard, keywords: 'cobranza cobro deuda vencido saldo pago pagos' },
  { label: 'Nuevo comprobante', path: '/comprobantes/nuevo', hint: 'Crear factura o boleta desde el flujo fiscal', icon: Receipt, keywords: 'comprobante factura boleta emitir documento' },
  { label: 'Facturas', path: '/facturas', hint: 'Comprobantes tipo 01', icon: Receipt, keywords: 'factura facturas sunat tipo 01' },
  { label: 'Boletas', path: '/boletas', hint: 'Comprobantes tipo 03', icon: Receipt, keywords: 'boleta boletas sunat tipo 03' },
  { label: 'Guias', path: '/guias', hint: 'Guias de remision y despacho', icon: Truck, keywords: 'guia guias remision gre despacho traslado' },
  { label: 'Notas credito/debito', path: '/notas', hint: 'Ajustes fiscales sobre comprobantes', icon: FileText, keywords: 'nota notas credito debito ajuste fiscal' },
  { label: 'Configuracion', path: '/configuracion', hint: 'Datos del negocio, logo, QR y seguridad', icon: Settings, keywords: 'configuracion negocio perfil cuenta logo qr seguridad' },
  { label: 'Diseno PDF', path: '/diseno-pdf', hint: 'Colores y textos de documentos comerciales', icon: Settings, keywords: 'pdf diseno plantilla colores cotizacion factura boleta' },
  { label: 'Superadmin', path: '/superadmin', hint: 'Tenants, usuarios y Smart PSE', icon: ShieldCheck, keywords: 'superadmin tenant usuarios smart pse gre', superadminOnly: true },
];

const SEARCH_TARGETS = [
  { label: 'Buscar clientes', path: '/clientes', hint: 'Razon social, RUC, DNI, correo o telefono' },
  { label: 'Buscar cotizaciones', path: '/cotizaciones', hint: 'Cliente, orden o numero de cotizacion', params: { view: 'history' } },
  { label: 'Buscar productos', path: '/productos', hint: 'Nombre, codigo interno o SKU' },
  { label: 'Buscar cobranza', path: '/cobranza', hint: 'Cliente, documento o saldo en seguimiento' },
];

function buildRoute(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

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
  const { user, loading, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const searchRef = useRef(null);
  const notificationsRef = useRef(null);
  const profileRef = useRef(null);
  const [openPanel, setOpenPanel] = useState(null);
  const [globalSearch, setGlobalSearch] = useState('');
  const [isContentScrolled, setIsContentScrolled] = useState(false);
  const [notificationsSeen, setNotificationsSeen] = useState(() =>
    localStorage.getItem('inkora-topbar-notifications-seen') === '1',
  );

  const meta = getRouteMeta(location.pathname);
  const isSuperadmin = Boolean(user?.is_superadmin);
  const userName = user?.nombre_completo || user?.email || 'Usuario Inkora';
  const userRole = isSuperadmin ? 'Superadmin' : user?.rol || 'Usuario';
  const userInitial = userName[0]?.toUpperCase() || 'U';

  const searchModules = useMemo(
    () => SEARCH_MODULES.filter((item) => !item.superadminOnly || isSuperadmin),
    [isSuperadmin],
  );

  const searchTargetActions = useMemo(() => {
    const current = SEARCH_TARGETS.find((item) => location.pathname.startsWith(item.path));
    return current
      ? [current, ...SEARCH_TARGETS.filter((item) => item.path !== current.path)]
      : SEARCH_TARGETS;
  }, [location.pathname]);

  const normalizedGlobalSearch = globalSearch.trim().toLowerCase();
  const routeMatches = useMemo(() => {
    if (!normalizedGlobalSearch) return searchModules.slice(0, 6);
    return searchModules
      .filter((item) =>
        `${item.label} ${item.hint} ${item.keywords}`.toLowerCase().includes(normalizedGlobalSearch),
      )
      .slice(0, 6);
  }, [normalizedGlobalSearch, searchModules]);

  const searchActions = useMemo(() => {
    const query = globalSearch.trim();
    if (!query) return [];
    return searchTargetActions.map((target) => ({
      ...target,
      to: buildRoute(target.path, { ...target.params, q: query }),
    }));
  }, [globalSearch, searchTargetActions]);

  const notifications = useMemo(() => {
    const items = [
      {
        title: 'Beta sin SUNAT real',
        text: 'La operacion fiscal real queda bloqueada hasta go fiscal escrito.',
        path: '/configuracion',
        tone: 'info',
      },
      {
        title: 'Revisar cobranza',
        text: 'Valida saldos vencidos y pagos pendientes antes de operar la beta.',
        path: '/cobranza',
        tone: 'warning',
      },
      {
        title: 'PDF comercial',
        text: 'Logo, QR y colores se gestionan desde configuracion y diseno PDF.',
        path: '/diseno-pdf',
        tone: 'info',
      },
    ];
    if (isSuperadmin) {
      items.push({
        title: 'Gobierno de tenants',
        text: 'Superadmin concentra altas, usuarios y estado Smart PSE.',
        path: '/superadmin',
        tone: 'info',
      });
    }
    return items;
  }, [isSuperadmin]);

  const unreadNotifications = notificationsSeen ? 0 : notifications.length;

  useEffect(() => {
    const handleOutside = (event) => {
      if (
        searchRef.current?.contains(event.target)
        || notificationsRef.current?.contains(event.target)
        || profileRef.current?.contains(event.target)
      ) {
        return;
      }
      setOpenPanel(null);
    };
    const handleKeydown = (event) => {
      if (event.key === 'Escape') setOpenPanel(null);
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', handleKeydown);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('keydown', handleKeydown);
    };
  }, []);

  const closePanel = () => setOpenPanel(null);

  const goTo = (to) => {
    navigate(to);
    setGlobalSearch('');
    closePanel();
  };

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    if (globalSearch.trim()) {
      goTo(searchActions[0]?.to || buildRoute('/clientes', { q: globalSearch.trim() }));
      return;
    }
    if (routeMatches[0]) goTo(routeMatches[0].path);
  };

  const openNotifications = () => {
    setOpenPanel((current) => (current === 'notifications' ? null : 'notifications'));
    setNotificationsSeen(true);
    localStorage.setItem('inkora-topbar-notifications-seen', '1');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;

  if (user.must_change_password && !location.pathname.startsWith('/configuracion')) {
    return <Navigate to="/configuracion?tab=seguridad" replace />;
  }

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
        <header
          className={cn(
            'app-topbar sticky top-0 z-30 grid min-h-[72px] flex-shrink-0 grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 border-b border-[var(--color-border)] bg-[rgba(255,255,255,0.94)] px-4 backdrop-blur-[18px] transition-shadow duration-200 sm:px-6',
            isContentScrolled && 'shadow-[0_8px_20px_rgba(18,30,24,0.08)]',
          )}
        >
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

          <div ref={searchRef} className="relative hidden sm:block">
            <form
              onSubmit={handleSearchSubmit}
              className={cn(
                'flex h-[42px] w-[210px] items-center gap-2.5 rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface-soft)] px-4 text-[var(--color-text-soft)] transition-all duration-200 lg:w-[250px]',
                openPanel === 'search' && 'border-[var(--color-primary)] bg-[var(--color-surface)] shadow-[var(--shadow-soft)]',
              )}
            >
              <Search size={14} className="flex-shrink-0" />
              <input
                value={globalSearch}
                onChange={(event) => setGlobalSearch(event.target.value)}
                onFocus={() => setOpenPanel('search')}
                placeholder="Buscar en Inkora..."
                className="min-w-0 flex-1 bg-transparent text-[12px] font-medium text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-soft)]"
                aria-label="Buscar en Inkora"
              />
            </form>

            {openPanel === 'search' && (
              <div className="absolute right-0 top-[calc(100%+10px)] z-50 w-[360px] overflow-hidden rounded-[18px] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-floating)]">
                <div className="border-b border-[var(--color-border)] px-4 py-3">
                  <p className="m-0 text-[11px] font-black uppercase tracking-[0.14em] text-[var(--color-text-muted)]">
                    Busqueda global
                  </p>
                  <p className="m-0 mt-1 text-[12px] text-[var(--color-text-muted)]">
                    Navega modulos o envia una consulta a una lista.
                  </p>
                </div>

                {searchActions.length > 0 && (
                  <div className="border-b border-[var(--color-border)] p-2">
                    {searchActions.slice(0, 4).map((item) => (
                      <button
                        key={item.to}
                        type="button"
                        onClick={() => goTo(item.to)}
                        className="flex w-full items-center gap-3 rounded-[13px] px-3 py-2.5 text-left transition-colors hover:bg-[var(--color-surface-soft)]"
                      >
                        <span className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-xl bg-[var(--color-primary-soft)] text-[var(--color-primary-text)]">
                          <Search size={14} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13px] font-extrabold text-[var(--color-text)]">
                            {item.label}: "{globalSearch.trim()}"
                          </span>
                          <span className="block truncate text-[11px] text-[var(--color-text-muted)]">
                            {item.hint}
                          </span>
                        </span>
                        <ArrowRight size={14} className="text-[var(--color-text-soft)]" />
                      </button>
                    ))}
                  </div>
                )}

                <div className="p-2">
                  {routeMatches.length > 0 ? (
                    routeMatches.map(({ label, hint, path, icon: Icon }) => (
                      <button
                        key={path}
                        type="button"
                        onClick={() => goTo(path)}
                        className="flex w-full items-center gap-3 rounded-[13px] px-3 py-2.5 text-left transition-colors hover:bg-[var(--color-surface-soft)]"
                      >
                        <span className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-xl border border-[var(--color-border)] text-[var(--color-text-muted)]">
                          <Icon size={14} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13px] font-bold text-[var(--color-text)]">{label}</span>
                          <span className="block truncate text-[11px] text-[var(--color-text-muted)]">{hint}</span>
                        </span>
                      </button>
                    ))
                  ) : (
                    <div className="px-3 py-4 text-[12px] text-[var(--color-text-muted)]">
                      Sin modulos coincidentes. Usa las opciones de busqueda superior.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="flex flex-shrink-0 items-center gap-2">
            <SunatStatus />

            <div ref={notificationsRef} className="relative">
              <button
                type="button"
                className="relative inline-flex h-[42px] w-[42px] items-center justify-center rounded-[13px] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] shadow-[var(--shadow-soft)] transition-colors hover:text-[var(--color-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2"
                aria-label="Ver notificaciones"
                aria-controls="topbar-notifications"
                aria-expanded={openPanel === 'notifications'}
                title="Notificaciones"
                onClick={openNotifications}
              >
                <Bell size={15} />
                {unreadNotifications > 0 && (
                  <span className="absolute right-[9px] top-[8px] h-[7px] w-[7px] rounded-full border border-white bg-[var(--color-primary)]" />
                )}
              </button>

              {openPanel === 'notifications' && (
                <div id="topbar-notifications" className="fixed left-3 right-3 top-[76px] z-50 overflow-hidden rounded-[18px] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-floating)] sm:absolute sm:left-auto sm:right-0 sm:top-[calc(100%+10px)] sm:w-[340px]">
                  <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
                    <div>
                      <p className="m-0 text-[11px] font-black uppercase tracking-[0.14em] text-[var(--color-text-muted)]">
                        Notificaciones
                      </p>
                      <p className="m-0 mt-1 text-[12px] text-[var(--color-text-muted)]">
                        Avisos operativos de beta.
                      </p>
                    </div>
                    <span className="rounded-full bg-[var(--color-primary-soft)] px-2.5 py-1 text-[10px] font-black uppercase text-[var(--color-primary-text)]">
                      {notifications.length}
                    </span>
                  </div>
                  <div className="p-2">
                    {notifications.map((item) => (
                      <button
                        key={item.title}
                        type="button"
                        onClick={() => goTo(item.path)}
                        className="flex w-full items-start gap-3 rounded-[13px] px-3 py-3 text-left transition-colors hover:bg-[var(--color-surface-soft)]"
                      >
                        <span
                          className={cn(
                            'mt-0.5 h-2.5 w-2.5 flex-shrink-0 rounded-full',
                            item.tone === 'warning' ? 'bg-[var(--color-warning)]' : 'bg-[var(--color-primary)]',
                          )}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block text-[13px] font-extrabold text-[var(--color-text)]">{item.title}</span>
                          <span className="mt-1 block text-[12px] leading-5 text-[var(--color-text-muted)]">{item.text}</span>
                        </span>
                        <ArrowRight size={14} className="mt-1 text-[var(--color-text-soft)]" />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div ref={profileRef} className="relative">
            <button
              type="button"
              className="inline-flex h-[42px] w-[42px] items-center justify-center rounded-[13px] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] shadow-[var(--shadow-soft)] transition-colors hover:text-[var(--color-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2"
              aria-label="Abrir menú de usuario"
              aria-controls="topbar-user-menu"
              aria-expanded={openPanel === 'profile'}
              title="Usuario"
              onClick={() => setOpenPanel((current) => (current === 'profile' ? null : 'profile'))}
            >
              <User size={15} />
            </button>

            {openPanel === 'profile' && (
              <div id="topbar-user-menu" className="absolute right-0 top-[calc(100%+10px)] z-50 w-[300px] overflow-hidden rounded-[18px] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-floating)]">
                <div className="border-b border-[var(--color-border)] p-4">
                  <div className="flex items-center gap-3">
                    <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-[#e3e941] to-[#7cc63f] text-[14px] font-black text-white">
                      {userInitial}
                    </span>
                    <div className="min-w-0">
                      <p className="m-0 truncate text-[14px] font-extrabold text-[var(--color-text)]">{userName}</p>
                      <p className="m-0 mt-0.5 truncate text-[12px] text-[var(--color-text-muted)]">{user?.email}</p>
                    </div>
                  </div>
                  <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-[var(--color-primary-soft)] px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-[var(--color-primary-text)]">
                    <ShieldCheck size={11} />
                    {userRole}
                  </div>
                </div>
                <div className="p-2">
                  <button
                    type="button"
                    onClick={() => goTo('/configuracion')}
                    className="flex w-full items-center gap-3 rounded-[13px] px-3 py-2.5 text-left text-[13px] font-bold text-[var(--color-text)] transition-colors hover:bg-[var(--color-surface-soft)]"
                  >
                    <Settings size={15} className="text-[var(--color-text-muted)]" />
                    Configuracion
                  </button>
                  <button
                    type="button"
                    onClick={() => goTo('/configuracion?tab=seguridad')}
                    className="flex w-full items-center gap-3 rounded-[13px] px-3 py-2.5 text-left text-[13px] font-bold text-[var(--color-text)] transition-colors hover:bg-[var(--color-surface-soft)]"
                  >
                    <ShieldCheck size={15} className="text-[var(--color-text-muted)]" />
                    Seguridad
                  </button>
                  {isSuperadmin && (
                    <button
                      type="button"
                      onClick={() => goTo('/superadmin')}
                      className="flex w-full items-center gap-3 rounded-[13px] px-3 py-2.5 text-left text-[13px] font-bold text-[var(--color-text)] transition-colors hover:bg-[var(--color-surface-soft)]"
                    >
                      <ShieldCheck size={15} className="text-[var(--color-text-muted)]" />
                      Superadmin
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="mt-1 flex w-full items-center gap-3 rounded-[13px] px-3 py-2.5 text-left text-[13px] font-bold text-[var(--color-danger-text)] transition-colors hover:bg-[var(--color-danger-soft)]"
                  >
                    <LogOut size={15} />
                    Cerrar sesion
                  </button>
                </div>
              </div>
            )}
            </div>

            <button
              className="hidden items-center gap-2 rounded-[18px] bg-[var(--color-dark-btn)] px-4 py-3 text-[14px] font-extrabold text-white transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2 sm:flex lg:px-6 lg:text-[16px]"
              type="button"
              onClick={() => navigate('/comprobantes/nuevo')}
              aria-label="Crear comprobante"
            >
              Crear comprobante
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/15">
                <Plus size={11} strokeWidth={2.5} />
              </span>
            </button>
            <button
              className="inline-flex h-[42px] w-[42px] items-center justify-center rounded-[13px] bg-[var(--color-dark-btn)] text-white shadow-[var(--shadow-soft)] transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2 sm:hidden"
              type="button"
              onClick={() => navigate('/comprobantes/nuevo')}
              aria-label="Crear comprobante"
            >
              <Plus size={18} strokeWidth={2.5} />
            </button>
          </div>
        </header>

        <SubscriptionBanner user={user} />

        <main
          className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 sm:py-7"
          onScroll={(event) => setIsContentScrolled(event.currentTarget.scrollTop > 4)}
        >
          <PageTransition>
            <Outlet />
          </PageTransition>
        </main>
      </div>
    </div>
  );
}
