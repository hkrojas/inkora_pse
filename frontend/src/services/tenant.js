import { api } from '../lib/utils/api';

export const tenant = {
  get:                (options = {}) => api.get('/tenant/', options),
  update:             (data) => api.put('/tenant/', data),
  uploadLogo:         (data) => api.postForm('/users/upload-logo', data, { timeoutMs: 30000 }),
  onboarding:         ()     => api.get('/onboarding/estado'),
  subscriptionStatus: ()     => api.get('/tenant/subscription-status'),
};
