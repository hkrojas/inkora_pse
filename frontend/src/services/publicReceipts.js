import { api } from '../lib/utils/api';

export const publicReceipts = {
  lookup: (data, options) => api.post('/public/comprobantes/consulta', data, options),
};
