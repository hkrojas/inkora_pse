import { api } from '../lib/utils/api';

export const productos = {
  list:         (params = '') => api.get(`/productos/${params}`),
  page:         (params = '') => api.get(`/productos/page${params}`),
  search:       (q, limit = 20, options = {}) => api.get(`/productos/search?q=${encodeURIComponent(q)}&limit=${limit}`, options),
  get:          (id)          => api.get(`/productos/${id}`),
  create:       (data)        => api.post('/productos/', data),
  update:       (id, data)    => api.put(`/productos/${id}`, data),
  remove:       (id)          => api.delete(`/productos/${id}`),
  generateCode: ()            => api.get('/productos/codigo-sugerido'),
};
