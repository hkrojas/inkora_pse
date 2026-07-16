import { api } from '../lib/utils/api';

export const cotizaciones = {
  list:    (params = '?limit=500') => api.get(`/cotizaciones/${params}`),
  fiscalPage: (params = '?limit=100&tab=all') => api.get(`/facturas-emitidas/page${params}`),
  get:     (id)          => api.get(`/cotizaciones/${id}`),
  create:  (data)        => api.post('/cotizaciones/', data),
  update:  (id, data)    => api.put(`/cotizaciones/${id}`, data),
  duplicar:(id)          => api.post(`/cotizaciones/${id}/duplicar`, {}),
  pdf:     (id)          => api.get(`/cotizaciones/${id}/pdf`),
  share:   (id)          => api.get(`/cotizaciones/${id}/compartir`),
  facturar:(id, payload) => api.post(`/cotizaciones/${id}/facturar`, payload),
  pagos:   (id)          => api.get(`/cotizaciones/${id}/pagos`),
  addPago: (id, data)    => api.post(`/cotizaciones/${id}/pagos`, data),
  notas:   (payload)     => api.post('/notas/emitir', payload),
  anular:  (payload)     => api.post('/bajas/anular', payload),
  remove:  (id)          => api.delete(`/cotizaciones/${id}`),
};
