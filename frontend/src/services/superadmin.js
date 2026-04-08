import { api } from '../lib/utils/api';

export const superadmin = {
  tenants:  ()     => api.get('/superadmin/tenants'),
  usuarios: ()     => api.get('/superadmin/usuarios'),
  auditLogs: ()    => api.get('/superadmin/audit-logs'),
  betaResumen: ()  => api.get('/superadmin/beta/resumen'),
};
