import { api } from '../lib/utils/api';
import { buildQueryString } from '../lib/utils/queryParams';

export const internalTransfers = {
  establishments: (includeInactive = false) => api.get(`/establecimientos${includeInactive ? '?include_inactive=true' : ''}`),
  createEstablishment: (data) => api.post('/establecimientos', data),
  updateEstablishment: (id, data) => api.put(`/establecimientos/${id}`, data),
  verifyEstablishment: (id, note) => api.post(`/establecimientos/${id}/verificar`, { note }),
  list: (params = { limit: 15 }) => api.get(`/traslados-internos${buildQueryString(params)}`),
  get: (id) => api.get(`/traslados-internos/${id}`),
  create: (data) => api.post('/traslados-internos', data),
  update: (id, data) => api.put(`/traslados-internos/${id}`, data),
  cancel: (id) => api.post(`/traslados-internos/${id}/cancelar`, {}),
  createDispatch: (id, data) => api.post(`/traslados-internos/${id}/despachos`, data),
  createGuide: (data) => api.post('/guias-remision/desde-traslado-interno', data),
  confirmDeparture: (dispatchId, idempotencyKey) => api.post(
    `/traslados-internos/despachos/${dispatchId}/confirmar-salida`,
    { idempotency_key: idempotencyKey },
  ),
  receive: (dispatchId, data) => api.post(`/traslados-internos/despachos/${dispatchId}/recepciones`, data),
};
