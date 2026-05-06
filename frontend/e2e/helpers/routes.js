export const MAIN_ROUTES = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/clientes', label: 'Clientes' },
  { path: '/productos', label: 'Productos' },
  { path: '/cotizaciones', label: 'Cotizaciones' },
  { path: '/comprobantes/nuevo', label: 'Crear comprobante' },
  { path: '/guias', label: 'Guias de remision' },
  { path: '/cobranza', label: 'Cobranza' },
  { path: '/configuracion', label: 'Configuracion' },
];

export const API_URL = process.env.E2E_API_URL || 'http://localhost:8000';
