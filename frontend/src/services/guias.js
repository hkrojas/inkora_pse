import { api } from '../lib/utils/api';

export const guias = {
  list:   (params = '') => api.get(`/guias-remision/${params}`),
  get:    (id)          => api.get(`/guias-remision/${id}`),
  create: (data)        => api.post('/guias-remision/', data),
};
