import { api } from '../lib/utils/api';

export const notas = {
  context: (documentId) => api.get(`/notas/contexto/${documentId}`),
  create: (data, idempotencyKey) => api.post('/notas/', data, {
    headers: { 'Idempotency-Key': idempotencyKey },
  }),
  update: (id, data) => api.patch(`/notas/${id}`, data),
  get: (id) => api.get(`/notas/${id}`),
  remove: (id) => api.delete(`/notas/${id}`),
  emit: (id) => api.post(`/notas/${id}/emitir?mode=async`, {}),
  job: (id) => api.get(`/emission-jobs/${id}`),
  replacement: (id) => api.post(`/notas/${id}/crear-reemplazo`, {}),
};
