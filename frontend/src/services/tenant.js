import { api } from '../lib/utils/api';

const TENANT_ASSET_UPLOAD_TIMEOUT_MS = 90000;

export const tenant = {
  get:                (options = {}) => api.get('/tenant/', options),
  update:             (data) => api.put('/tenant/', data),
  uploadLogo:         (data) => api.postForm('/users/upload-logo', data, { timeoutMs: TENANT_ASSET_UPLOAD_TIMEOUT_MS }),
  uploadPaymentQr:    (data) => api.postForm('/users/upload-payment-qr', data, { timeoutMs: TENANT_ASSET_UPLOAD_TIMEOUT_MS }),
  onboarding:         ()     => api.get('/onboarding/estado'),
  subscriptionStatus: ()     => api.get('/tenant/subscription-status'),
};
