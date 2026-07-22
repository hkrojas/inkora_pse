import { api } from '../lib/utils/api';

export const accessRequests = {
  create: (data) => api.post('/access-requests', data),
  status: (token) => api.post('/access-requests/status', { request_token: token }),
};
