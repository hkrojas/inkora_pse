import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { AlertTriangle, ShieldCheck, XCircle } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import { useAuth } from '../context/AuthContext';
import { FullPageSpinner } from '../components/ui/Spinner';
import { sunat } from '../services/sunat';
import { tenant as tenantSvc } from '../services/tenant';

function SunatExchangeRate() {
  const [exchangeRate, setExchangeRate] = useState(null);
  const [loadingRate, setLoadingRate] = useState(true);

  useEffect(() => {
    let mounted = true;
    let retryTimeoutId;

    const loadExchangeRate = async () => {
      try {
        const data = await sunat.exchangeRate();
        if (!mounted) return;
        setExchangeRate(data);
        retryTimeoutId = setTimeout(loadExchangeRate, 30 * 60 * 1000);
      } catch {
        if (!mounted) return;
        setExchangeRate(null);
        retryTimeoutId = setTimeout(loadExchangeRate, 60 * 1000);
      } finally {
        if (mounted) {
          setLoadingRate(false);
        }
      }
    };

    loadExchangeRate();

    return () => {
      mounted = false;
      clearTimeout(retryTimeoutId);
    };
  }, []);

  if (loadingRate) {
    return (
      <span className="sunat-rate-chip sunat-rate-chip--loading">
        <span className="sunat-rate-chip-label">TC SUNAT</span>
        <span className="sunat-rate-chip-block">
          <span className="sunat-rate-chip-key">Cargando</span>
          <span className="sunat-rate-chip-value">...</span>
        </span>
      </span>
    );
  }

  if (!exchangeRate) {
    return (
      <span className="sunat-rate-chip sunat-rate-chip--unavailable">
        <span className="sunat-rate-chip-label">TC SUNAT</span>
        <span className="sunat-rate-chip-block">
          <span className="sunat-rate-chip-key">Estado</span>
          <span className="sunat-rate-chip-value">No disponible</span>
        </span>
      </span>
    );
  }

  return (
    <span
      className={`sunat-rate-chip ${exchangeRate.stale ? 'sunat-rate-chip--stale' : ''}`}
      title={`SUNAT ${exchangeRate.date}`}
    >
      <span className="sunat-rate-chip-label">TC SUNAT</span>
      <span className="sunat-rate-chip-block">
        <span className="sunat-rate-chip-key">Compra</span>
        <span className="sunat-rate-chip-value">{exchangeRate.buy}</span>
      </span>
      <span className="sunat-rate-chip-separator" />
      <span className="sunat-rate-chip-block">
        <span className="sunat-rate-chip-key">Venta</span>
        <span className="sunat-rate-chip-value">{exchangeRate.sell}</span>
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
      const s = String(now.getSeconds()).padStart(2, '0');
      setTime(`${h}:${m}:${s}`);
      setDate(
        now.toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase()
        + ' - LIMA'
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="topbar-clock">
      <div className="topbar-clock-primary">
        <SunatExchangeRate />
        <span className="topbar-clock-time">{time}</span>
      </div>
      <span className="topbar-clock-date">{date}</span>
    </div>
  );
}

const ROUTE_META = {
  '/dashboard': {
    kicker: 'Resumen operativo',
    title: 'Panel Inkora',
    breadcrumb: 'Dashboard / Resumen',
  },
  '/clientes': {
    kicker: 'Relacion comercial',
    title: 'Clientes',
    breadcrumb: 'Maestros / Clientes',
  },
  '/productos': {
    kicker: 'Catalogo reusable',
    title: 'Productos y servicios',
    breadcrumb: 'Maestros / Productos',
  },
  '/cotizaciones': {
    kicker: 'Motor comercial',
    title: 'Cotizaciones',
    breadcrumb: 'Ventas / Cotizaciones',
  },
  '/cobranza': {
    kicker: 'Flujo de caja',
    title: 'Cobranza',
    breadcrumb: 'Ventas / Cobranza',
  },
  '/guias': {
    kicker: 'Despacho fiscal',
    title: 'Guias de remision',
    breadcrumb: 'Logistica / Guias',
  },
  '/facturas': {
    kicker: 'Comprobantes tipo 01',
    title: 'Facturas emitidas',
    breadcrumb: 'Facturacion / Facturas',
  },
  '/comprobantes/nuevo': {
    kicker: 'Emision central',
    title: 'Crear comprobante',
    breadcrumb: 'Facturacion / Crear comprobante',
  },
  '/boletas': {
    kicker: 'Comprobantes tipo 03',
    title: 'Boletas de venta',
    breadcrumb: 'Facturacion / Boletas',
  },
  '/notas': {
    kicker: 'Ajustes fiscales',
    title: 'Notas de Credito y Debito',
    breadcrumb: 'Ventas / Notas',
  },
  '/retenciones': {
    kicker: 'Regimen de retenciones',
    title: 'Retenciones',
    breadcrumb: 'SUNAT / Retenciones',
  },
  '/percepciones': {
    kicker: 'Regimen de percepciones',
    title: 'Percepciones',
    breadcrumb: 'SUNAT / Percepciones',
  },
  '/resumen-diario': {
    kicker: 'Consolidado de boletas',
    title: 'Resumen Diario',
    breadcrumb: 'SUNAT / Resumen Diario',
  },
  '/bajas': {
    kicker: 'Anulacion ante SUNAT',
    title: 'Comunicacion de Bajas',
    breadcrumb: 'SUNAT / Bajas',
  },
  '/reversiones': {
    kicker: 'Reversion de documentos',
    title: 'Reversiones',
    breadcrumb: 'SUNAT / Reversiones',
  },
  '/configuracion': {
    kicker: 'Datos del negocio',
    title: 'Perfil de empresa',
    breadcrumb: 'Sistema / Perfil',
  },
  '/cambiar-password': {
    kicker: 'Seguridad de cuenta',
    title: 'Cambiar contraseña',
    breadcrumb: 'Sistema / Contraseña',
  },
  '/diseno-pdf': {
    kicker: 'Plantilla comercial',
    title: 'Diseño PDF',
    breadcrumb: 'Sistema / Diseño PDF',
  },
  '/superadmin': {
    kicker: 'Control interno',
    title: 'Superadmin',
    breadcrumb: 'Sistema / Superadmin',
  },
};

function getRouteMeta(pathname) {
  if (pathname.startsWith('/cotizaciones/')) {
    return {
      kicker: 'Detalle comercial',
      title: 'Detalle de cotizacion',
      breadcrumb: 'Ventas / Cotizaciones / Detalle',
    };
  }

  if (pathname.startsWith('/guias/')) {
    return {
      kicker: 'Seguimiento de despacho',
      title: 'Detalle de guia',
      breadcrumb: 'Logistica / Guias / Detalle',
    };
  }

  return ROUTE_META[pathname] || {
    kicker: 'Operacion',
    title: 'Inkora',
    breadcrumb: 'Inkora',
  };
}

function SubscriptionBanner({ user }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    if (!user || user.is_superadmin || user.rol === 'superadmin') return;
    tenantSvc.subscriptionStatus()
      .then((data) => { if (data.message) setStatus(data); })
      .catch(() => {});
  }, [user]);

  if (!status) return null;

  const isBlocked = status.emission_blocked;
  const bgColor = isBlocked ? '#fef2f2' : '#fffbeb';
  const borderColor = isBlocked ? '#ef4444' : '#f59e0b';
  const textColor = isBlocked ? '#b91c1c' : '#92400e';
  const Icon = isBlocked ? XCircle : AlertTriangle;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '8px 20px',
      background: bgColor,
      borderBottom: `2px solid ${borderColor}`,
      color: textColor,
      fontSize: 13,
      fontWeight: 500,
    }}>
      <Icon style={{ width: 16, height: 16, flexShrink: 0 }} />
      <span>{status.message}</span>
    </div>
  );
}

export default function AppLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;

  // Forzar cambio de contraseña antes de acceder a cualquier pantalla
  if (user.must_change_password && location.pathname !== '/cambiar-password') {
    return <Navigate to="/cambiar-password" replace />;
  }

  const meta = getRouteMeta(location.pathname);
  const isSuperadmin = user?.is_superadmin || user?.rol === 'superadmin';

  return (
    <>
      <div className="topbar-tension-line" />
      <div className="app-shell">
        <Sidebar />

        <div className="app-main-shell">
          <header className="topbar-shell">
            <div className="topbar-main">
              <div className="topbar-mobile-row">
                <div className="topbar-breadcrumb">{meta.breadcrumb}</div>
              </div>
              <div className="topbar-title-row">
                <h1 className="topbar-title">{meta.title}</h1>
                {isSuperadmin && (
                  <span className="badge badge--outline">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    superadmin
                  </span>
                )}
              </div>
              <p className="topbar-kicker">{meta.kicker}</p>
            </div>

            <div className="topbar-actions">
              <SystemClock />
              <div className="topbar-divider" />
              <div className="sunat-badge">
                <span className="sunat-badge-dot" />
                SUNAT Sync
              </div>
            </div>
          </header>

          <SubscriptionBanner user={user} />

          <main className="app-content-shell">
            <Outlet />
          </main>
        </div>
      </div>
    </>
  );
}
