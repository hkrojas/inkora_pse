import { api } from '../lib/utils/api';

export const cobranza = {
  resumen: () => api.get('/cobranza/resumen'),
  vencidas: (params = '?scope=active&limit=50') => api.get(`/cobranza/vencidas${params}`),
};
