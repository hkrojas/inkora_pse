import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './components/ui/Toast';
import AppLayout from './layouts/AppLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ClientesPage from './pages/ClientesPage';
import ProductosPage from './pages/ProductosPage';
import CotizacionesPage from './pages/CotizacionesPage';
import CotizacionDetalle from './pages/CotizacionDetalle';
import CobranzaPage from './pages/CobranzaPage';
import GuiasPage from './pages/GuiasPage';
import GuiaDetalle from './pages/GuiaDetalle';
import ConfiguracionPage from './pages/ConfiguracionPage';
import PdfDesignerPage from './pages/PdfDesignerPage';
import SuperadminPage from './pages/SuperadminPage';
import NotasPage from './pages/NotasPage';
import RetencionesPage from './pages/RetencionesPage';
import PercepcionesPage from './pages/PercepcionesPage';
import ResumenDiarioPage from './pages/ResumenDiarioPage';
import BajasPage from './pages/BajasPage';
import ReversionesPage from './pages/ReversionesPage';
import FacturasPage from './pages/FacturasPage';
import BoletasPage from './pages/BoletasPage';
import ComprobanteNuevoPage from './pages/ComprobanteNuevoPage';
import ChangePasswordPage from './pages/ChangePasswordPage';

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/clientes" element={<ClientesPage />} />
              <Route path="/productos" element={<ProductosPage />} />
              <Route path="/cotizaciones" element={<CotizacionesPage />} />
              <Route path="/cotizaciones/:id" element={<CotizacionDetalle />} />
              <Route path="/cobranza" element={<CobranzaPage />} />
              <Route path="/guias" element={<GuiasPage />} />
              <Route path="/guias/:id" element={<GuiaDetalle />} />
              <Route path="/configuracion" element={<ConfiguracionPage />} />
              <Route path="/cambiar-password" element={<ChangePasswordPage />} />
              <Route path="/diseno-pdf" element={<PdfDesignerPage />} />
              <Route path="/superadmin" element={<SuperadminPage />} />
              <Route path="/comprobantes/nuevo" element={<ComprobanteNuevoPage />} />
              <Route path="/facturas" element={<FacturasPage />} />
              <Route path="/boletas" element={<BoletasPage />} />
              <Route path="/notas" element={<NotasPage />} />
              <Route path="/retenciones" element={<RetencionesPage />} />
              <Route path="/percepciones" element={<PercepcionesPage />} />
              <Route path="/resumen-diario" element={<ResumenDiarioPage />} />
              <Route path="/bajas" element={<BajasPage />} />
              <Route path="/reversiones" element={<ReversionesPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
