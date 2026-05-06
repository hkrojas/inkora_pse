import { expect } from '@playwright/test';
import { API_URL } from './routes';

const FETCH_RESOURCE_TYPES = new Set(['fetch', 'xhr']);

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function routeUrlPattern(path) {
  return new RegExp(`${escapeRegExp(path)}(?:$|[?#])`);
}

export async function assertUsableRoute(page, route) {
  await page.goto(route.path);
  await page.waitForLoadState('domcontentloaded');
  await expect(page).toHaveURL(routeUrlPattern(route.path));
  await expect(page.locator('#root')).toBeVisible();
  await page.waitForFunction(() => {
    const root = document.querySelector('#root');
    const text = root?.innerText?.trim() || '';
    return root && root.children.length > 0 && text.length > 20 && text !== 'Cargando...';
  });
  await expect(page.getByText('Cargando...', { exact: true })).toHaveCount(0);
}

export function attachCriticalErrorCollector(page) {
  const errors = [];

  page.on('pageerror', (error) => {
    errors.push(`pageerror: ${error.message}`);
  });

  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (/favicon/i.test(text)) return;
    errors.push(`console.error: ${text}`);
  });

  page.on('response', (response) => {
    const request = response.request();
    const type = request.resourceType();
    const status = response.status();
    if (type === 'script' && status >= 400) {
      errors.push(`script ${status}: ${response.url()}`);
    }
    if (FETCH_RESOURCE_TYPES.has(type) && status >= 500) {
      errors.push(`api ${status}: ${response.url()}`);
    }
  });

  return {
    assertClean() {
      expect(errors).toEqual([]);
    },
    errors,
  };
}

export function attachApiOriginGuard(page) {
  const allowedApiOrigin = new URL(API_URL).origin;
  const invalidApiRequests = [];

  page.on('request', (request) => {
    if (!FETCH_RESOURCE_TYPES.has(request.resourceType())) return;
    const origin = new URL(request.url()).origin;
    if (origin !== allowedApiOrigin) {
      invalidApiRequests.push(`${request.method()} ${request.url()}`);
    }
  });

  return {
    assertClean() {
      expect(invalidApiRequests).toEqual([]);
    },
    invalidApiRequests,
  };
}
