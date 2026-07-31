import { api } from '../lib/utils/api';

export const inventory = {
  warehouses: () => api.get('/inventario/almacenes'),
  createWarehouse: (data) => api.post('/inventario/almacenes', data),
  updateWarehouse: (id, data) => api.patch(`/inventario/almacenes/${id}`, data),
  activate: (data = {}) => api.post('/inventario/activar', data),
  stock: () => api.get('/inventario/existencias'),
  stockPage: (params = '?skip=0&limit=15') => api.get(`/inventario/existencias/page${params}`),
  movements: (params = '?skip=0&limit=15') => api.get(`/inventario/kardex${params}`),
  movementsPage: (params = '?skip=0&limit=15') => api.get(`/inventario/kardex/page${params}`),
  searchDocuments: (q, limit = 20, options = {}) => api.get(`/inventario/documentos/search?q=${encodeURIComponent(q)}&limit=${limit}`, options),
  adjust: (data) => api.post('/inventario/ajustes', data),
  bulkAdjust: (data) => api.post('/inventario/cargas', data),
  previewImport: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.postForm('/inventario/cargas/preview', formData, { timeoutMs: 30000 });
  },
  downloadTemplate: () => api.download('/inventario/cargas/plantilla'),
  transfer: (data) => api.post('/inventario/transferencias', data),
  availability: (data) => api.post('/inventario/disponibilidad', data),
  documentAvailability: (id) => api.get(`/inventario/documentos/${id}/disponibilidad`),
  configureProduct: (id, data) => api.put(`/inventario/productos/${id}`, data),
  returns: (params = '?skip=0&limit=15') => api.get(`/inventario/devoluciones${params}`),
  receiveReturn: (id, data) => api.post(`/inventario/devoluciones/${id}/recibir`, data),
};
