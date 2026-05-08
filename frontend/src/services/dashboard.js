import { api } from '../lib/utils/api';

const DASHBOARD_TIMEOUT_MS = 20000;

async function getWithRetry(path, fallback) {
  try {
    return await api.get(path, { timeoutMs: DASHBOARD_TIMEOUT_MS });
  } catch {
    try {
      return await api.get(path, { timeoutMs: DASHBOARD_TIMEOUT_MS });
    } catch {
      return fallback;
    }
  }
}

export const dashboard = {
  stats:       ()       => getWithRetry('/analytics/dashboard', null),
  cobranzaResumen: ()   => getWithRetry('/cobranza/resumen', null),
  cobranzaVencidas: (params = '?limit=4') => getWithRetry(`/cobranza/vencidas${params}`, []),
  reporteMensual: (anio, mes) => {
    if (!anio || !mes) {
      throw new Error('reporteMensual requiere anio y mes');
    }
    return api.get(`/reporte/mensual?anio=${encodeURIComponent(anio)}&mes=${encodeURIComponent(mes)}`, {
      timeoutMs: DASHBOARD_TIMEOUT_MS,
    });
  },

  // Documentos recientes para el dashboard
  recentDocuments: async () => {
    const data = await getWithRetry('/cotizaciones/?limit=4', []);
    return Array.isArray(data) ? data : [];
  },

  // Facturas vencidas para el bloque de cobranza del dashboard
  pendingInvoices: async () => {
    const data = await getWithRetry('/cobranza/vencidas?limit=4', []);
    return Array.isArray(data) ? data : [];
  },
};
