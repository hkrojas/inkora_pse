import { api } from '../lib/utils/api';

export const inventory = {
  warehouses: () => api.get('/inventario/almacenes'),
  createWarehouse: (data) => api.post('/inventario/almacenes', data),
  activate: (data = {}) => api.post('/inventario/activar', data),
  stock: () => api.get('/inventario/existencias'),
  movements: (params = '?skip=0&limit=15') => api.get(`/inventario/kardex${params}`),
  movementsPage: (params = '?skip=0&limit=15') => api.get(`/inventario/kardex/page${params}`),
  adjust: (data) => api.post('/inventario/ajustes', data),
  transfer: (data) => api.post('/inventario/transferencias', data),
  availability: (data) => api.post('/inventario/disponibilidad', data),
  documentAvailability: (id) => api.get(`/inventario/documentos/${id}/disponibilidad`),
  configureProduct: (id, data) => api.put(`/inventario/productos/${id}`, data),
  returns: (params = '?skip=0&limit=15') => api.get(`/inventario/devoluciones${params}`),
  receiveReturn: (id, data) => api.post(`/inventario/devoluciones/${id}/recibir`, data),
};
