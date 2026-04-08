import { api } from '../lib/utils/api';

export const dashboard = {
  stats:       ()       => api.get('/analytics/dashboard'),
  cobranzaResumen: ()   => api.get('/cobranza/resumen'),
  cobranzaVencidas: ()  => api.get('/cobranza/vencidas'),
  reporteMensual: ()    => api.get('/reporte/mensual'),
};
