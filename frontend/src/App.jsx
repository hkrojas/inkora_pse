import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './components/ui/Toast';
import AppLayout from './layouts/AppLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

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

function LazyRoute({ children }) {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>;
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
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
              <Route path="/retenciones" element={<LazyRoute><RetencionesPage /></LazyRoute>} />
              <Route path="/percepciones" element={<LazyRoute><PercepcionesPage /></LazyRoute>} />
              <Route path="/resumen-diario" element={<LazyRoute><ResumenDiarioPage /></LazyRoute>} />
              <Route path="/bajas" element={<LazyRoute><BajasPage /></LazyRoute>} />
              <Route path="/reversiones" element={<LazyRoute><ReversionesPage /></LazyRoute>} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
