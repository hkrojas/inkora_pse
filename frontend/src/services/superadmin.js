import { api } from '../lib/utils/api';

export const superadmin = {
  tenants:      ()              => api.get('/superadmin/tenants'),
  createTenant: (data)          => api.post('/superadmin/tenants', data),
  updateTenant: (id, data)      => api.patch(`/superadmin/tenants/${id}`, data),
  deleteTenant: (id)            => api.delete(`/superadmin/tenants/${id}`),
  consultarDocumento: (numero)  => api.get(`/consultar-documento/${numero}`),
  validateApisPeruToken: (data) => api.post('/superadmin/validate/apisperu-token', data),
  createUser:   (tenantId, data) => api.post(`/superadmin/tenants/${tenantId}/users`, data),
  usuarios:     ()              => api.get('/superadmin/usuarios'),
  auditLogs:    ()              => api.get('/superadmin/audit-logs'),
  betaResumen:  ()              => api.get('/superadmin/beta/resumen'),
};
