import { BASE_URL } from './config';

function getStoredToken() {
  return localStorage.getItem('token') || sessionStorage.getItem('token');
}

function clearStoredToken() {
  localStorage.removeItem('token');
  sessionStorage.removeItem('token');
}

function getApiErrorMessage(detail, fallback) {
  if (typeof detail === 'string') return detail;
  if (detail?.message) return detail.message;
  return fallback;
}

async function request(path, options = {}) {
  const token = getStoredToken();
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
    const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
    const message = getApiErrorMessage(errorData.detail, 'Error en la peticion');
    const normalizedMessage = message.toLowerCase();
    const shouldEndSession = response.status === 401 || (
      response.status === 403
      && (
        normalizedMessage.includes('usuario se encuentra bloqueado')
        || normalizedMessage.includes('tenant se encuentra suspendido')
      )
    );

    if (shouldEndSession) {
      clearStoredToken();
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    throw new Error(message);
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
