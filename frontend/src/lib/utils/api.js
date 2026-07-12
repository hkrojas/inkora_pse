import { BASE_URL } from './config.js';

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

function buildApiError(message, {
  status = null,
  path = '',
  isTimeout = false,
  isCanceled = false,
} = {}) {
  const error = new Error(message);
  error.status = status;
  error.path = path;
  error.isTimeout = isTimeout;
  error.isCanceled = isCanceled;
  return error;
}

function bindAbortSignal(controller, signal, timeoutMs) {
  let timeoutReached = false;
  const timeoutId = setTimeout(() => {
    timeoutReached = true;
    controller.abort('timeout');
  }, timeoutMs);
  const forwardAbort = () => controller.abort(signal?.reason || 'external');
  if (signal?.aborted) {
    forwardAbort();
  } else if (signal) {
    signal.addEventListener('abort', forwardAbort, { once: true });
  }
  return {
    didTimeout: () => timeoutReached,
    cleanup: () => {
      clearTimeout(timeoutId);
      if (signal) signal.removeEventListener('abort', forwardAbort);
    },
  };
}

async function request(path, options = {}) {
  const { timeoutMs = 12000, signal, ...fetchOptions } = options;
  const token = getStoredToken();
  const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData;
  const headers = {
    ...fetchOptions.headers,
  };

  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const abortBinding = bindAbortSignal(controller, signal, timeoutMs);

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      if (!abortBinding.didTimeout()) {
        throw buildApiError('Solicitud cancelada.', {
          path,
          isCanceled: true,
        });
      }
      throw buildApiError('La solicitud tardó demasiado. Revisa el backend e inténtalo nuevamente.', {
        path,
        isTimeout: true,
      });
    }
    throw buildApiError(error?.message || 'No se pudo conectar con el backend.', { path });
  } finally {
    abortBinding.cleanup();
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
    const message = getApiErrorMessage(errorData.detail, 'Error en la petición');
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

    throw buildApiError(message, { status: response.status, path });
  }

  return response.json();
}

async function requestBlob(path, options = {}) {
  const { timeoutMs = 30000, signal, ...fetchOptions } = options;
  const token = getStoredToken();
  const headers = {
    ...fetchOptions.headers,
    'Content-Type': 'application/json',
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const abortBinding = bindAbortSignal(controller, signal, timeoutMs);

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      if (!abortBinding.didTimeout()) {
        throw buildApiError('Descarga cancelada.', {
          path,
          isCanceled: true,
        });
      }
      throw buildApiError('La descarga tardó demasiado. Inténtalo nuevamente.', {
        path,
        isTimeout: true,
      });
    }
    throw buildApiError(error?.message || 'No se pudo conectar con el backend.', { path });
  } finally {
    abortBinding.cleanup();
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Error descargando archivo' }));
    throw buildApiError(getApiErrorMessage(errorData.detail, 'Error descargando archivo'), {
      status: response.status,
      path,
    });
  }

  return {
    blob: await response.blob(),
    contentType: response.headers.get('Content-Type') || 'application/octet-stream',
    disposition: response.headers.get('Content-Disposition') || '',
  };
}

export const api = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  getBlob: (path, options) => requestBlob(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body: JSON.stringify(body) }),
  blob: (path, body, options) => requestBlob(path, { ...options, method: 'POST', body: JSON.stringify(body) }),
  postForm: (path, formData, options) => request(path, { ...options, method: 'POST', body: formData }),
  put: (path, body, options) => request(path, { ...options, method: 'PUT', body: JSON.stringify(body) }),
  patch: (path, body, options) => request(path, { ...options, method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
};
