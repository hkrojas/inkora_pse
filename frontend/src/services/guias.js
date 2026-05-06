import { api } from '../lib/utils/api';
import { buildQueryString } from '../lib/utils/queryParams';

export const guias = {
  list:   (params = { limit: 15 }) => api.get(`/guias-remision/${buildQueryString(params)}`),
  get:    (id)          => api.get(`/guias-remision/${id}`),
  create: (data)        => api.post('/guias-remision/', data),
};
