import { api } from '../lib/utils/api';

export const dashboard = {
  stats:       ()       => api.get('/analytics/dashboard'),
  cobranzaResumen: ()   => api.get('/cobranza/resumen'),
  cobranzaVencidas: ()  => api.get('/cobranza/vencidas'),
  reporteMensual: ()    => api.get('/reporte/mensual'),

  // Documentos recientes para el dashboard
  recentDocuments: async () => {
    const data = await api.get('/cotizaciones/');
    return Array.isArray(data) ? data : [];
  },

  // Facturas vencidas para el bloque de cobranza del dashboard
  pendingInvoices: async () => {
    const data = await api.get('/cobranza/vencidas');
    return Array.isArray(data) ? data : [];
  },
};
