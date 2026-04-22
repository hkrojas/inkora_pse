import { api } from '../lib/utils/api';

export const tenant = {
  get:                ()     => api.get('/tenant/'),
  update:             (data) => api.put('/tenant/', data),
  onboarding:         ()     => api.get('/onboarding/estado'),
  subscriptionStatus: ()     => api.get('/tenant/subscription-status'),
};
