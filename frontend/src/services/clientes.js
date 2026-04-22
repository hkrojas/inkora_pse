import { api } from '../lib/utils/api';

export const clientes = {
  list:   (params = '') => api.get(`/clientes/${params}`),
  get:    (id)          => api.get(`/clientes/${id}`),
  lookupDocument: (numero) => api.get(`/consultar-documento/${numero}`),
  create: (data)        => api.post('/clientes/', data),
  update: (id, data)    => api.put(`/clientes/${id}`, data),
  remove: (id)          => api.delete(`/clientes/${id}`),
};
