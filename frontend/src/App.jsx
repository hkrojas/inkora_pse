import { Component, lazy, Suspense } from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './components/ui/Toast';
import AppLayout from './layouts/AppLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import { ENABLE_ADVANCED_FISCAL } from './lib/utils/config';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const AccessRequestPage = lazy(() => import('./pages/AccessRequestPage'));
const PasswordRecoveryPage = lazy(() => import('./pages/PasswordRecoveryPage'));
const ClientesPage = lazy(() => import('./pages/ClientesPage'));
const ProductosPage = lazy(() => import('./pages/ProductosPage'));
const CotizacionesPage = lazy(() => import('./pages/CotizacionesPage'));
const CotizacionDetalle = lazy(() => import('./pages/CotizacionDetalle'));
const CobranzaPage = lazy(() => import('./pages/CobranzaPage'));
const GuiasPage = lazy(() => import('./pages/GuiasPage'));
const GuiaDetalle = lazy(() => import('./pages/GuiaDetalle'));
const ConfiguracionPage = lazy(() => import('./pages/ConfiguracionPage'));
const PdfDesignerPage = lazy(() => import('./pages/PdfDesignerPage'));
const SuperadminPage = lazy(() => import('./pages/SuperadminPage'));
const NotasPage = lazy(() => import('./pages/NotasPage'));
const NotaNuevaPage = lazy(() => import('./pages/NotaNuevaPage'));
const InventarioPage = lazy(() => import('./pages/InventarioPage'));
const RetencionesPage = lazy(() => import('./pages/RetencionesPage'));
const PercepcionesPage = lazy(() => import('./pages/PercepcionesPage'));
const ResumenDiarioPage = lazy(() => import('./pages/ResumenDiarioPage'));
const BajasPage = lazy(() => import('./pages/BajasPage'));
const ReversionesPage = lazy(() => import('./pages/ReversionesPage'));
const FacturasPage = lazy(() => import('./pages/FacturasPage'));
const BoletasPage = lazy(() => import('./pages/BoletasPage'));
const ComprobanteNuevoPage = lazy(() => import('./pages/ComprobanteNuevoPage'));

function RouteFallback() {
  return (
    <div className="flex min-h-[280px] items-center justify-center px-4 text-sm text-[var(--color-text-muted)]">
      Cargando...
    </div>
  );
}

class RouteErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-[320px] items-center justify-center px-4">
        <article className="panel max-w-lg p-7">
          <p className="eyebrow">Error de carga</p>
          <h2 className="m-0 text-[24px] font-extrabold tracking-[-0.04em] text-[var(--color-text)]">
            No se pudo cargar esta seccion
          </h2>
          <p className="mt-3 text-sm leading-6 text-[var(--color-text-muted)]">
            Actualiza la pagina para cargar la version mas reciente de Inkora.
          </p>
          <button type="button" className="btn-primary mt-6" onClick={() => window.location.reload()}>
            Actualizar
          </button>
        </article>
      </div>
    );
  }
}

function LazyRoute({ children }) {
  const location = useLocation();
  return (
    <RouteErrorBoundary resetKey={location.pathname}>
      <Suspense fallback={<RouteFallback />}>{children}</Suspense>
    </RouteErrorBoundary>
  );
}

function AdvancedFiscalBlockedPage() {
  return (
    <div className="page-shell">
      <article className="panel mx-auto max-w-2xl p-8">
        <p className="eyebrow">Beta prepago</p>
        <h2 className="m-0 text-[24px] font-extrabold tracking-[-0.04em] text-[var(--color-text)]">
          Operacion fiscal avanzada no habilitada
        </h2>
        <p className="mt-3 text-sm leading-6 text-[var(--color-text-muted)]">
          Este flujo queda bloqueado durante la beta sin SUNAT real. Para operar la demo usa
          comprobantes, guias, cobranza y Smart PSE CPE en ambiente demo.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link className="btn-primary" to="/dashboard">Volver al dashboard</Link>
          <Link className="btn-secondary" to="/comprobantes/nuevo">Crear comprobante</Link>
        </div>
      </article>
    </div>
  );
}

function AdvancedFiscalRoute({ children }) {
  if (ENABLE_ADVANCED_FISCAL) return children;
  return <AdvancedFiscalBlockedPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/" element={<LazyRoute><LandingPage /></LazyRoute>} />
            <Route path="/presentacion" element={<LazyRoute><LandingPage /></LazyRoute>} />
            <Route path="/login" element={<Login />} />
            <Route path="/recuperar-password" element={<LazyRoute><PasswordRecoveryPage /></LazyRoute>} />
            <Route path="/solicitar-acceso" element={<LazyRoute><AccessRequestPage /></LazyRoute>} />
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/clientes" element={<LazyRoute><ClientesPage /></LazyRoute>} />
              <Route path="/productos" element={<LazyRoute><ProductosPage /></LazyRoute>} />
              <Route path="/cotizaciones" element={<LazyRoute><CotizacionesPage /></LazyRoute>} />
              <Route path="/cotizaciones/:id" element={<LazyRoute><CotizacionDetalle /></LazyRoute>} />
              <Route path="/cobranza" element={<LazyRoute><CobranzaPage /></LazyRoute>} />
              <Route path="/guias" element={<LazyRoute><GuiasPage /></LazyRoute>} />
              <Route path="/guias/:id" element={<LazyRoute><GuiaDetalle /></LazyRoute>} />
              <Route path="/configuracion" element={<LazyRoute><ConfiguracionPage /></LazyRoute>} />
              <Route path="/cambiar-password" element={<Navigate to="/configuracion?tab=seguridad" replace />} />
              <Route path="/diseno-pdf" element={<LazyRoute><PdfDesignerPage /></LazyRoute>} />
              <Route path="/superadmin" element={<LazyRoute><SuperadminPage /></LazyRoute>} />
              <Route path="/comprobantes/nuevo" element={<LazyRoute><ComprobanteNuevoPage /></LazyRoute>} />
              <Route path="/facturas" element={<LazyRoute><FacturasPage /></LazyRoute>} />
              <Route path="/boletas" element={<LazyRoute><BoletasPage /></LazyRoute>} />
              <Route path="/notas" element={<LazyRoute><NotasPage /></LazyRoute>} />
              <Route path="/notas/nueva" element={<LazyRoute><NotaNuevaPage /></LazyRoute>} />
              <Route path="/inventario" element={<LazyRoute><InventarioPage /></LazyRoute>} />
              <Route path="/retenciones" element={<AdvancedFiscalRoute><LazyRoute><RetencionesPage /></LazyRoute></AdvancedFiscalRoute>} />
              <Route path="/percepciones" element={<AdvancedFiscalRoute><LazyRoute><PercepcionesPage /></LazyRoute></AdvancedFiscalRoute>} />
              <Route path="/resumen-diario" element={<AdvancedFiscalRoute><LazyRoute><ResumenDiarioPage /></LazyRoute></AdvancedFiscalRoute>} />
              <Route path="/bajas" element={<AdvancedFiscalRoute><LazyRoute><BajasPage /></LazyRoute></AdvancedFiscalRoute>} />
              <Route path="/reversiones" element={<AdvancedFiscalRoute><LazyRoute><ReversionesPage /></LazyRoute></AdvancedFiscalRoute>} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
