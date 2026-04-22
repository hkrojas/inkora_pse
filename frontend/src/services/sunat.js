import { api } from '../lib/utils/api';

export const sunat = {
  exchangeRate: () => api.get('/sunat/exchange-rate'),
};
