import { api } from '../lib/utils/api';
import { buildQueryString } from '../lib/utils/queryParams';

export const superadmin = {
  // Tenants
  tenants:              ()              => api.get('/superadmin/tenants'),
  tenantsPage:          (params)        => api.get(`/superadmin/tenants-page${buildQueryString(params)}`),
  createTenant:         (data)          => api.post('/superadmin/tenants', data),
  updateTenant:         (id, data)      => api.patch(`/superadmin/tenants/${id}`, data),
  deleteTenant:         (id)            => api.delete(`/superadmin/tenants/${id}`),
  consultarDocumento:   (numero)        => api.get(`/consultar-documento/${numero}`),
  validateApisPeruToken:(data)          => api.post('/superadmin/validate/apisperu-token', data),
  updateSmartPseGreCredentials: (tenantId, data) => api.put(`/superadmin/tenants/${tenantId}/smartpse/gre-credentials`, data),
  checkSmartPseGreCredentials:  (tenantId)       => api.post(`/superadmin/tenants/${tenantId}/smartpse/gre-credentials/check`),

  // Usuarios
  createUser:           (tenantId, data) => api.post(`/superadmin/tenants/${tenantId}/users`, data),
  usuarios:             ()              => api.get('/superadmin/usuarios'),
  tenantUsersDetail:    (tenantId)      => api.get(`/superadmin/tenants/${tenantId}/users-detail`),
  toggleUserActive:     (userId, isActive) => api.patch(`/superadmin/users/${userId}/toggle-active`, { is_active: isActive }),
  resetUserPassword:    (userId)        => api.post(`/superadmin/users/${userId}/reset-password`),
  updateUser:           (userId, data)  => api.patch(`/superadmin/users/${userId}`, data),
  deleteUser:           (userId)        => api.delete(`/superadmin/users/${userId}`),

  // Health & errores
  checkTokenHealth:     (tenantId)      => api.post(`/superadmin/tenants/${tenantId}/check-token-health`),
  checkAllTokens:       ()              => api.post('/superadmin/check-all-tokens'),
  emissionErrors:       (tenantId, limit = 50) => api.get(`/superadmin/tenants/${tenantId}/emission-errors?limit=${limit}`),

  // Limites de emision (Fase 2)
  tenantLimits:         (tenantId)      => api.get(`/superadmin/tenants/${tenantId}/limits`),
  upsertTenantLimits:   (tenantId, limits) => api.put(`/superadmin/tenants/${tenantId}/limits`, { limits }),
  deleteLimit:          (limitId)       => api.delete(`/superadmin/limits/${limitId}`),
  fiscalFlags:          (tenantId)      => api.get(`/superadmin/tenants/${tenantId}/fiscal-flags`),
  updateFiscalFlags:    (tenantId, flags) => api.put(`/superadmin/tenants/${tenantId}/fiscal-flags`, { flags }),

  // Suscripciones
  auditLogs:            ()              => api.get('/superadmin/audit-logs'),
  betaResumen:          ()              => api.get('/superadmin/beta/resumen'),
  tenantActividad:      (tenantId)      => api.get(`/superadmin/tenants/${tenantId}/actividad`),
  tenantsDetail:        ()              => api.get('/superadmin/tenants-detail'),
  subscription:         (tenantId)      => api.get(`/superadmin/tenants/${tenantId}/subscription`),
  activateTenant:       (tenantId, data) => api.post(`/superadmin/tenants/${tenantId}/activate`, data),
  suspendTenant:        (tenantId, data) => api.post(`/superadmin/tenants/${tenantId}/suspend`, data),
  extendAccess:         (tenantId, data) => api.post(`/superadmin/tenants/${tenantId}/extend-access`, data),
  registerPayment:      (tenantId, data) => api.post(`/superadmin/tenants/${tenantId}/payments`, data),
  listPayments:         (tenantId)      => api.get(`/superadmin/tenants/${tenantId}/payments`),
  updateNotas:          (tenantId, data) => api.patch(`/superadmin/tenants/${tenantId}/notas`, data),
};
