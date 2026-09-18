import { expect, test } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const EXPECTED_API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;

const tenant = {
  id: 384,
  business_name: 'PAPELERIA GRAFICA Y PUBLICITARIA SAC.',
  business_ruc: '20606751509',
  business_address: 'Lima',
  plan_type: 'founder',
  is_active: true,
  has_apisperu_token: false,
  has_smartpse_gre_credentials: false,
};

const superadmin = {
  id: 1,
  email: 'superadmin.qa@inkora.test',
  nombre_completo: 'Superadmin QA',
  rol: 'superadmin',
  is_superadmin: true,
  must_change_password: false,
  tenant_id: null,
};

function inactiveStatus(overrides = {}) {
  return {
    tenant_id: tenant.id,
    enabled: false,
    reason: null,
    started_at: null,
    held_jobs: 0,
    released_jobs: 0,
    processing_jobs: 0,
    pending_confirmation_jobs: 0,
    ...overrides,
  };
}

function activeStatus(overrides = {}) {
  return {
    tenant_id: tenant.id,
    enabled: true,
    reason: 'Smart PSE devuelve error 0111',
    started_at: '2026-08-31T11:20:00',
    held_jobs: 3,
    released_jobs: 0,
    processing_jobs: 1,
    pending_confirmation_jobs: 1,
    ...overrides,
  };
}

async function createMockedSuperadminContext(browser, baseURL, options = {}) {
  const state = {
    status: options.status || inactiveStatus(),
    patchBodies: [],
    unexpectedRequests: [],
    wrongApiOrigins: [],
  };
  const context = await browser.newContext({
    baseURL,
    viewport: options.viewport,
    storageState: { cookies: [], origins: [] },
  });
  await context.addInitScript(() => {
    localStorage.setItem('token', 'fiscal-contingency-smoke-token');
    sessionStorage.removeItem('token');
  });
  const page = await context.newPage();
  const criticalErrors = attachCriticalErrorCollector(page);

  await page.route('**/*', async (route) => {
    const request = route.request();
    if (!['fetch', 'xhr'].includes(request.resourceType())) {
      await route.continue();
      return;
    }

    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    const method = request.method();
    if (url.origin !== EXPECTED_API_ORIGIN) {
      state.wrongApiOrigins.push(`${method} ${request.url()}`);
    }

    let payload;
    if (path === '/users/me' && method === 'GET') {
      payload = superadmin;
    } else if (path === '/sunat/exchange-rate' && method === 'GET') {
      payload = { buy: '3.512', sell: '3.522' };
    } else if (path === '/superadmin/tenants-page' && method === 'GET') {
      payload = {
        items: [tenant],
        total: 1,
        skip: 0,
        limit: 25,
        metrics: {
          total: 1,
          active: 1,
          smartpse_gre: 0,
          smartpse_gre_pending: 1,
        },
      };
    } else if (path === `/superadmin/tenants/${tenant.id}/fiscal-contingency` && method === 'GET') {
      payload = state.status;
    } else if (path === `/superadmin/tenants/${tenant.id}/fiscal-contingency` && method === 'PATCH') {
      const body = request.postDataJSON();
      state.patchBodies.push(body);
      state.status = body.enabled
        ? activeStatus({ reason: body.reason })
        : inactiveStatus({ released_jobs: 3, pending_confirmation_jobs: 1 });
      payload = state.status;
    } else {
      state.unexpectedRequests.push(`${method} ${request.url()}`);
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'API no simulada en fiscal-contingency.spec.js' }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    });
  });

  return { context, page, state, criticalErrors };
}

function assertSafeNetworkAndConsole(state, criticalErrors) {
  expect(state.unexpectedRequests).toEqual([]);
  expect(state.wrongApiOrigins).toEqual([]);
  criticalErrors.assertClean();
}

async function openContingencyModal(page) {
  await page.goto('/superadmin');
  await expect(page.getByRole('heading', { name: /^Superadmin$/i, level: 2 })).toBeVisible();
  await page.getByRole('button', { name: /^Contingencia$/i }).click();
  await expect(page.getByRole('heading', { name: /Contingencia fiscal/i })).toBeVisible();
}

test.describe('contingencia fiscal Superadmin con API simulada', () => {
  test('activa con motivo y comunica que SUNAT aun no acepto los comprobantes', async ({ browser, baseURL }) => {
    const { context, page, state, criticalErrors } = await createMockedSuperadminContext(browser, baseURL);

    try {
      await openContingencyModal(page);
      await expect(page.getByRole('heading', { name: /Operación fiscal normal/i })).toBeVisible();

      const activateButton = page.getByRole('button', { name: /Activar contingencia/i });
      await expect(activateButton).toBeDisabled();
      await page.getByLabel(/Motivo del incidente/i).fill('Smart PSE devuelve error 0111');
      await activateButton.click();

      await expect(page.getByRole('heading', { name: /En contingencia/i })).toBeVisible();
      await expect(page.getByText(/no se envían al proveedor fiscal/i)).toBeVisible();
      await expect(page.getByText(/3 comprobantes retenidos/i)).toBeVisible();
      expect(state.patchBodies).toEqual([{
        enabled: true,
        reason: 'Smart PSE devuelve error 0111',
      }]);

      const retainedCard = page.locator('.ink-card').filter({ hasText: 'Retenidos' }).first();
      await expect(retainedCard.getByText('3', { exact: true })).toBeVisible();
      await expect(page.getByText(/no se reintentan automáticamente/i)).toBeVisible();
      assertSafeNetworkAndConsole(state, criticalErrors);
    } finally {
      await context.close();
    }
  });

  test('libera solamente después de la segunda confirmación y mantiene aislados los ambiguos', async ({ browser, baseURL }) => {
    const { context, page, state, criticalErrors } = await createMockedSuperadminContext(browser, baseURL, {
      status: activeStatus(),
    });

    try {
      await openContingencyModal(page);
      await expect(page.getByText(/documentos pendientes de confirmación permanecerán aislados/i)).toBeVisible();

      await page.getByRole('button', { name: /Preparar liberación/i }).click();
      await expect(page.getByText(/Confirma la liberación de 3 comprobantes/i)).toBeVisible();
      expect(state.patchBodies).toEqual([]);

      await page.getByRole('button', { name: /Confirmar y reanudar/i }).click();
      await expect(page.getByRole('heading', { name: /Operación fiscal normal/i })).toBeVisible();
      await expect(page.getByText(/Se liberaron 3 comprobantes de forma escalonada/i)).toBeVisible();
      expect(state.patchBodies).toEqual([{ enabled: false }]);
      expect(state.status.pending_confirmation_jobs).toBe(1);
      assertSafeNetworkAndConsole(state, criticalErrors);
    } finally {
      await context.close();
    }
  });

  test('el modal activo es usable en móvil sin desborde horizontal', async ({ browser, baseURL }) => {
    const { context, page, state, criticalErrors } = await createMockedSuperadminContext(browser, baseURL, {
      status: activeStatus(),
      viewport: { width: 390, height: 844 },
    });

    try {
      await openContingencyModal(page);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(2);
      assertSafeNetworkAndConsole(state, criticalErrors);
    } finally {
      await context.close();
    }
  });
});
