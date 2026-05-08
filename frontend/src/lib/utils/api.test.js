import test from 'node:test';
import assert from 'node:assert/strict';
import { api } from './api.js';

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }

  getItem(key) {
    return this.values.get(key) || null;
  }

  setItem(key, value) {
    this.values.set(key, String(value));
  }

  removeItem(key) {
    this.values.delete(key);
  }

  clear() {
    this.values.clear();
  }
}

function installBrowserGlobals() {
  global.localStorage = new MemoryStorage();
  global.sessionStorage = new MemoryStorage();
  global.window = { location: { pathname: '/dashboard', href: '' } };
}

test('api.get marks external aborts as canceled', async () => {
  installBrowserGlobals();
  const controller = new AbortController();
  global.fetch = (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => {
      const error = new Error('aborted');
      error.name = 'AbortError';
      reject(error);
    });
  });

  const request = api.get('/tenant/', { signal: controller.signal, timeoutMs: 1000 });
  controller.abort();

  await assert.rejects(request, (error) => {
    assert.equal(error.isCanceled, true);
    assert.equal(error.isTimeout, false);
    assert.equal(error.path, '/tenant/');
    return true;
  });
});

test('api.get marks internal request timeout separately', async () => {
  installBrowserGlobals();
  global.fetch = (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => {
      const error = new Error('aborted');
      error.name = 'AbortError';
      reject(error);
    });
  });

  await assert.rejects(api.get('/slow', { timeoutMs: 5 }), (error) => {
    assert.equal(error.isTimeout, true);
    assert.equal(error.isCanceled, false);
    assert.equal(error.path, '/slow');
    return true;
  });
});

test('api.get clears stored token and redirects on 401', async () => {
  installBrowserGlobals();
  localStorage.setItem('token', 'stale-token');
  global.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Sesion vencida' }),
  });

  await assert.rejects(api.get('/tenant/'), (error) => {
    assert.equal(error.status, 401);
    assert.equal(error.path, '/tenant/');
    return true;
  });

  assert.equal(localStorage.getItem('token'), null);
  assert.equal(window.location.href, '/login');
});
