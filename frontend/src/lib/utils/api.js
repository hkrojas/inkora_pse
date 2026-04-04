const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const token = localStorage.getItem('token');
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers = {
    ...options.headers
  };

  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    // Handle unauthorized globally
    if (response.status === 401) {
      localStorage.removeItem('token');
      // window.location.href = '/login'; // Optional: handled by store
    }
    const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(errorData.detail || 'Error en la petición');
  }

  return response.json();
}

export const api = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body: JSON.stringify(body) }),
  postForm: (path, formData, options) => request(path, { ...options, method: 'POST', body: formData }),
  put: (path, body, options) => request(path, { ...options, method: 'PUT', body: JSON.stringify(body) }),
  patch: (path, body, options) => request(path, { ...options, method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
};
