import { expect, test } from '@playwright/test';

const API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000';

const user = {
  id: 701,
  email: 'tenant.beta@inkora.test',
  nombre_completo: 'Tenant Beta',
  rol: 'admin',
  is_superadmin: false,
  must_change_password: false,
  tenant_id: 7,
};

const tenant = {
  id: 7,
  business_name: 'DEMO SMART PSE SAC',
  business_ruc: '20609999991',
  business_address: 'Av. Demo 456',
  plan_type: 'founder',
  is_active: true,
  has_smartpse_credentials: true,
  smartpse_status: 'ok',
  smartpse_checked_at: '2026-05-18T12:00:00Z',
  smartpse_environment: 'demo',
  has_smartpse_gre_credentials: true,
  smartpse_gre_status: 'ok',
  smartpse_gre_checked_at: '2026-05-18T12:00:00Z',
};

const ADVANCED_FISCAL_ROUTES = [
  '/resumen-diario',
  '/bajas',
  '/reversiones',
  '/retenciones',
  '/percepciones',
];

async function createBetaContext(browser, baseURL, options = {}) {
  const context = await browser.newContext({
    baseURL,
    storageState: { cookies: [], origins: [] },
  });
  await context.addInitScript(() => {
    localStorage.setItem('token', 'beta-scope-token');
    sessionStorage.removeItem('token');
  });

  const page = await context.newPage();
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    if (options.onApiRequest) options.onApiRequest(request, path);

    const payload = getApiPayload(path);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    });
  });

  return { context, page };
}

function getApiPayload(path) {
  if (path === '/users/me') return user;
  if (path === '/tenant') return tenant;
  if (path === '/tenant/subscription-status') return {};
  if (path === '/sunat/exchange-rate') return { buy: '3.512', sell: '3.522' };
  if (path === '/dashboard/summary') return {};
  if (path === '/clientes' || path === '/productos' || path === '/cotizaciones') return [];
  return {};
}

test.describe('beta launch scope', () => {
  test('tenant no ve accesos fiscales avanzados en el menu beta', async ({ browser, baseURL }) => {
    const { context, page } = await createBetaContext(browser, baseURL);

    try {
      await page.goto('/dashboard');
      await expect(page.getByRole('heading', { name: /Dashboard/i })).toBeVisible();

      for (const route of ADVANCED_FISCAL_ROUTES) {
        await expect(page.locator(`a[href="${route}"]`)).toHaveCount(0);
      }
    } finally {
      await context.close();
    }
  });

  test('dashboard apila seguimiento sin hueco entre tarjetas principales', async ({ browser, baseURL }) => {
    const { context, page } = await createBetaContext(browser, baseURL);

    try {
      for (const viewport of [
        { width: 1366, height: 900 },
        { width: 390, height: 844 },
      ]) {
        await page.setViewportSize(viewport);
        await page.goto('/dashboard');

        const activityPanel = page.getByRole('heading', { name: /Actividad reciente/i }).locator('xpath=ancestor::article[1]');
        const followPanel = page.getByRole('heading', { name: /Seguimiento de cobranza/i }).locator('xpath=ancestor::article[1]');

        await expect(activityPanel).toBeVisible();
        await expect(followPanel).toBeVisible();

        const gap = await page.evaluate(() => {
          const activity = document
            .evaluate("//h3[contains(., 'Actividad reciente')]/ancestor::article[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)
            .singleNodeValue;
          const follow = document
            .evaluate("//h3[contains(., 'Seguimiento de cobranza')]/ancestor::article[1]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)
            .singleNodeValue;
          if (!activity || !follow) return Number.POSITIVE_INFINITY;
          return follow.getBoundingClientRect().top - activity.getBoundingClientRect().bottom;
        });

        expect(gap).toBeGreaterThanOrEqual(0);
        expect(gap).toBeLessThanOrEqual(24);
      }
    } finally {
      await context.close();
    }
  });

  test('urls fiscales avanzadas quedan bloqueadas sin cargar flujos reales', async ({ browser, baseURL }) => {
    const apiRequests = [];
    const { context, page } = await createBetaContext(browser, baseURL, {
      onApiRequest: (request, path) => {
        apiRequests.push(`${request.method()} ${path}`);
      },
    });

    try {
      for (const route of ADVANCED_FISCAL_ROUTES) {
        await page.goto(route);
        await expect(page.getByRole('heading', { name: /Operacion fiscal avanzada no habilitada/i })).toBeVisible();
        await expect(page.getByText(/beta sin SUNAT real/i)).toBeVisible();
      }

      for (const route of ADVANCED_FISCAL_ROUTES) {
        expect(apiRequests.some((entry) => entry.includes(route))).toBe(false);
      }
    } finally {
      await context.close();
    }
  });
});
