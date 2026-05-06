import { api } from '../lib/utils/api';

export const productos = {
  list:         (params = '') => api.get(`/productos/${params}`),
  page:         (params = '') => api.get(`/productos/page${params}`),
  get:          (id)          => api.get(`/productos/${id}`),
  create:       (data)        => api.post('/productos/', data),
  update:       (id, data)    => api.put(`/productos/${id}`, data),
  remove:       (id)          => api.delete(`/productos/${id}`),
  generateCode: ()            => api.get('/productos/codigo-sugerido'),
};
