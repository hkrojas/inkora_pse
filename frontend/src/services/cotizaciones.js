import { api } from '../lib/utils/api';

export const cotizaciones = {
  list:    (params = '') => api.get(`/cotizaciones/${params}`),
  get:     (id)          => api.get(`/cotizaciones/${id}`),
  create:  (data)        => api.post('/cotizaciones/', data),
  pdf:     (id)          => api.get(`/cotizaciones/${id}/pdf`),
  share:   (id)          => api.get(`/cotizaciones/${id}/compartir`),
  facturar:(id, payload) => api.post(`/cotizaciones/${id}/facturar`, payload),
  pagos:   (id)          => api.get(`/cotizaciones/${id}/pagos`),
  addPago: (id, data)    => api.post(`/cotizaciones/${id}/pagos`, data),
};
