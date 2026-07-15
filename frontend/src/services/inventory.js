import { api } from '../lib/utils/api';

export const inventory = {
  warehouses: () => api.get('/inventario/almacenes'),
  activate: (data = {}) => api.post('/inventario/activar', data),
  stock: () => api.get('/inventario/existencias'),
  movements: () => api.get('/inventario/kardex?limit=15'),
  adjust: (data) => api.post('/inventario/ajustes', data),
  transfer: (data) => api.post('/inventario/transferencias', data),
  availability: (data) => api.post('/inventario/disponibilidad', data),
  configureProduct: (id, data) => api.put(`/inventario/productos/${id}`, data),
  returns: () => api.get('/inventario/devoluciones'),
  receiveReturn: (id, data) => api.post(`/inventario/devoluciones/${id}/recibir`, data),
};
