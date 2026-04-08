import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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
import SuperadminPage from './pages/SuperadminPage';

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<AppLayout />}>
              <Route path="/dashboard"       element={<Dashboard />} />
              <Route path="/clientes"        element={<ClientesPage />} />
              <Route path="/productos"       element={<ProductosPage />} />
              <Route path="/cotizaciones"    element={<CotizacionesPage />} />
              <Route path="/cotizaciones/:id" element={<CotizacionDetalle />} />
              <Route path="/cobranza"        element={<CobranzaPage />} />
              <Route path="/guias"           element={<GuiasPage />} />
              <Route path="/guias/:id"       element={<GuiaDetalle />} />
              <Route path="/configuracion"   element={<ConfiguracionPage />} />
              <Route path="/superadmin"      element={<SuperadminPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
