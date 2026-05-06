import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { expect } from '@playwright/test';

export const TENANT_STORAGE_STATE = '.playwright/.auth/tenant.json';
const AUTH_TIMEOUT_MS = 30_000;

function getApiOrigin() {
  return new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
}

function isApiResponse(response, { method, path }) {
  const url = new URL(response.url());
  return (
    url.origin === getApiOrigin()
    && url.pathname.replace(/\/$/, '') === path.replace(/\/$/, '')
    && response.request().method() === method
  );
}

async function getResponseText(response) {
  const text = await response.text().catch(() => '');
  return text
    .replace(/"access_token"\s*:\s*"[^"]+"/gi, '"access_token":"[redacted]"')
    .replace(/Bearer\s+[A-Za-z0-9._-]+/g, 'Bearer [redacted]')
    .slice(0, 500);
}

async function getTokenStorageState(page) {
  return page.evaluate(() => ({
    localStorage: Boolean(localStorage.getItem('token')),
    sessionStorage: Boolean(sessionStorage.getItem('token')),
  })).catch(() => ({ localStorage: false, sessionStorage: false }));
}

async function assertOkResponse(response, label) {
  if (response.ok()) return;
  const body = await getResponseText(response);
  throw new Error(`${label} fallo con status ${response.status()}: ${body}`);
}

export function requireTenantCredentials() {
  const missing = ['E2E_TENANT_EMAIL', 'E2E_TENANT_PASSWORD'].filter(
    (key) => !process.env[key],
  );
  if (missing.length) {
    throw new Error(
      `Faltan variables E2E requeridas: ${missing.join(', ')}. `
      + 'Definelas antes de ejecutar Playwright.',
    );
  }
  return {
    email: process.env.E2E_TENANT_EMAIL,
    password: process.env.E2E_TENANT_PASSWORD,
  };
}

export async function loginTenantByUi(page) {
  const { email, password } = requireTenantCredentials();
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: /bienvenido de vuelta/i })).toBeVisible();
  await page.getByLabel(/correo|usuario/i).fill(email);
  await page.locator('input[autocomplete="current-password"]').fill(password);
  const tokenResponsePromise = page.waitForResponse(
    (response) => isApiResponse(response, { method: 'POST', path: '/token' }),
    { timeout: AUTH_TIMEOUT_MS },
  );
  const meResponsePromise = page.waitForResponse(
    (response) => isApiResponse(response, { method: 'GET', path: '/users/me/' }),
    { timeout: AUTH_TIMEOUT_MS },
  ).catch((error) => ({ error }));

  await page.getByRole('button', { name: /acceder al dashboard/i }).click();

  const tokenResponse = await tokenResponsePromise;
  await assertOkResponse(tokenResponse, 'POST /token');

  await page.waitForFunction(
    () => Boolean(localStorage.getItem('token') || sessionStorage.getItem('token')),
    undefined,
    { timeout: AUTH_TIMEOUT_MS },
  );

  const meResponse = await meResponsePromise;
  if (meResponse.error) {
    const storage = await getTokenStorageState(page);
    throw new Error(
      `GET /users/me/ no completo en ${AUTH_TIMEOUT_MS}ms. `
      + `tokenStorage local=${storage.localStorage} session=${storage.sessionStorage}`,
    );
  }
  await assertOkResponse(meResponse, 'GET /users/me/');

  await expect(page).toHaveURL(/\/dashboard(?:$|[?#])/, { timeout: AUTH_TIMEOUT_MS });
  await expect(page.getByText(/dashboard/i).first()).toBeVisible({ timeout: AUTH_TIMEOUT_MS });
}

export async function saveTenantStorageState(page) {
  mkdirSync(dirname(TENANT_STORAGE_STATE), { recursive: true });
  await page.context().storageState({ path: TENANT_STORAGE_STATE });
}
