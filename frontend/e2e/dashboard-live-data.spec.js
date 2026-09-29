import { expect, test } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;

const tenant = {
  id: 73,
  business_name: 'Inkora Dashboard QA',
  business_ruc: '20123456789',
  business_address: 'Lima',
  plan_type: 'founder',
  is_active: true,
};

const user = {
  id: 7301,
  email: 'dashboard.e2e@inkora.test',
  nombre_completo: 'Operador Dashboard',
  rol: 'admin',
  is_superadmin: false,
  must_change_password: false,
  tenant_id: tenant.id,
};

const dashboardPayload = {
  meta: {
    generated_at: '2026-09-28T12:30:00-05:00',
    currency: 'PEN',
    period: { start: '2026-09-01', end: '2026-09-28', label: '1–28 sep 2026' },
    comparison: { start: '2026-08-01', end: '2026-08-28', label: '1–28 ago 2026' },
    history: { start: '2026-01-01', end: '2026-09-28', label: '1 ene – 28 sep 2026' },
    client_id: null,
    product_id: null,
  },
  summary: {
    sales_amount: '12345.00',
    sales_count: 3,
    pending_sunat_amount: '432.00',
    sales_change_percent: '23.4',
    customers_count: 4,
    new_customers_count: 1,
    returning_customers_count: 3,
    average_sale: '4115.00',
    overdue_amount: '987.00',
    overdue_customers_count: 2,
  },
  history: [
    { year: 2026, month: 1, sales_amount: '1100.00', quoted_amount: '1400.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 2, sales_amount: '2100.00', quoted_amount: '2400.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 3, sales_amount: '3100.00', quoted_amount: '3400.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 4, sales_amount: '4100.00', quoted_amount: '4400.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 5, sales_amount: '5100.00', quoted_amount: '5400.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 6, sales_amount: '6100.00', quoted_amount: '6400.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 7, sales_amount: '7100.00', quoted_amount: '7400.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 8, sales_amount: '10004.00', quoted_amount: '10500.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 9, sales_amount: '12345.00', quoted_amount: '13000.00', is_partial: true, cutoff_day: 28, previous_matched_sales: '10004.00' },
  ],
  conversion: {
    available: false,
    reason: 'quote_origin_not_recorded',
    quote_count: null,
    linked_sales_count: null,
    rate_percent: null,
  },
  products: [
    { id: 911, name: 'Resma API Única', unit: 'NIU', quantity: '7.00', amount: '7777.00', previous_amount: '7000.00', change_percent: '11.1' },
    { id: 912, name: 'Tinta API Azul', unit: 'NIU', quantity: '4.00', amount: '4568.00', previous_amount: '5000.00', change_percent: '-8.6' },
  ],
  clients: [
    { id: 731, name: 'Cliente API Único', amount: '8000.00', purchases: 2, last_purchase: '2026-09-25', share_percent: '64.8', previous_amount: '7000.00', change_percent: '14.3' },
    { id: 732, name: 'Cliente API Dos', amount: '4345.00', purchases: 1, last_purchase: '2026-09-20', share_percent: '35.2', previous_amount: '3004.00', change_percent: '44.6' },
  ],
  follow_up: {
    quotes: { available: false, reason: 'quote_origin_not_recorded', count: 0, rows: [] },
    declining: {
      available: true,
      reason: null,
      count: 1,
      rows: [{ client_id: 732, client: 'Cliente API Dos', reference: 'Ventas del periodo', amount: '4345.00', age_days: 8 }],
    },
    inactive: {
      available: true,
      reason: null,
      count: 1,
      rows: [{ client_id: 733, client: 'Cliente API Inactivo', reference: 'Última compra', amount: '900.00', age_days: 68 }],
    },
  },
  pending: {
    low_stock_products: 6,
    fiscal_documents_with_errors: 2,
  },
};

function emptyDashboardPayload() {
  return {
    ...dashboardPayload,
    summary: {
      sales_amount: '0.00',
      sales_count: 0,
      pending_sunat_amount: '0.00',
      sales_change_percent: null,
      customers_count: 0,
      new_customers_count: 0,
      returning_customers_count: 0,
      average_sale: '0.00',
      overdue_amount: '0.00',
      overdue_customers_count: 0,
    },
    history: dashboardPayload.history.map((row) => ({
      ...row,
      sales_amount: '0.00',
      quoted_amount: '0.00',
      previous_matched_sales: row.is_partial ? '0.00' : null,
    })),
    products: [],
    clients: [],
    follow_up: {
      quotes: { available: false, reason: 'quote_origin_not_recorded', count: 0, rows: [] },
      declining: { available: true, reason: null, count: 0, rows: [] },
      inactive: { available: true, reason: null, count: 0, rows: [] },
    },
    pending: { low_stock_products: 0, fiscal_documents_with_errors: 0 },
  };
}

async function createDashboardContext(browser, baseURL, options = {}) {
  const state = {
    dashboardCalls: [],
    unexpectedRequests: [],
  };
  const context = await browser.newContext({
    baseURL,
    viewport: options.viewport || { width: 1280, height: 900 },
    storageState: { cookies: [], origins: [] },
  });
  await context.addInitScript(() => localStorage.setItem('token', 'dashboard-live-data-e2e-token'));
  const page = await context.newPage();

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    const method = request.method();

    if (path === '/users/me' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) });
      return;
    }
    if (path === '/tenant/subscription-status' && method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      return;
    }
    if (path === '/sunat/exchange-rate' && method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ compra: 3.7, venta: 3.72, moneda: 'USD' }),
      });
      return;
    }
    if (path === '/analytics/dashboard/business' && method === 'GET') {
      state.dashboardCalls.push({
        url: request.url(),
        authorization: request.headers().authorization,
      });
      const call = state.dashboardCalls.length;
      if (options.delayMs) await new Promise((resolve) => setTimeout(resolve, options.delayMs));
      if (options.failRequests && call <= options.failRequests) {
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Dashboard temporalmente no disponible' }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(options.payload || dashboardPayload),
      });
      return;
    }

    state.unexpectedRequests.push(`${method} ${request.url()}`);
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'API no simulada en dashboard-live-data.spec.js' }),
    });
  });

  return { context, page, state };
}

test.describe('Dashboard conectado al contrato business', () => {
  test('renderiza exclusivamente los datos del endpoint autenticado', async ({ browser, baseURL }) => {
    const { context, page, state } = await createDashboardContext(browser, baseURL);
    const errors = attachCriticalErrorCollector(page);
    try {
      await page.goto('/dashboard');

      await expect(page.getByTestId('dashboard-business-mockup')).toBeVisible();
      await expect(page.getByText('Resma API Única')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Cliente API Único', exact: true })).toBeVisible();
      await expect(page.getByText(/S\/\s*12[,.]345/).first()).toBeVisible();
      await expect(page.getByText('Datos de ejemplo')).toHaveCount(0);
      await expect(page.getByText('Papel bond A4', { exact: true })).toHaveCount(0);

      expect(state.dashboardCalls).toHaveLength(1);
      expect(state.dashboardCalls.every(({ authorization }) => (
        authorization === 'Bearer dashboard-live-data-e2e-token'
      ))).toBe(true);
      expect(state.dashboardCalls.every(({ url }) => (
        new URL(url).pathname === '/analytics/dashboard/business'
      ))).toBe(true);
      expect(state.unexpectedRequests).toEqual([]);
      errors.assertClean();
    } finally {
      await context.close();
    }
  });

  test('distingue una respuesta vacía de un error', async ({ browser, baseURL }) => {
    const { context, page, state } = await createDashboardContext(browser, baseURL, {
      payload: emptyDashboardPayload(),
    });
    try {
      await page.goto('/dashboard');

      await expect(page.getByTestId('dashboard-business-mockup')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Aún no hay actividad para mostrar' })).toBeVisible();
      await expect(page.getByText('Cuando registres ventas, clientes o movimientos pendientes, el resumen aparecerá aquí.')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Reintentar' })).toHaveCount(0);
      await expect(page.getByText('Resma API Única')).toHaveCount(0);
      expect(state.dashboardCalls).toHaveLength(1);
      expect(state.unexpectedRequests).toEqual([]);
    } finally {
      await context.close();
    }
  });

  test('conserva el historial cuando el periodo actual no tiene ventas', async ({ browser, baseURL }) => {
    const payload = emptyDashboardPayload();
    payload.history[0] = { ...payload.history[0], sales_amount: '750.00' };
    const { context, page } = await createDashboardContext(browser, baseURL, { payload });
    try {
      await page.goto('/dashboard');

      await expect(page.getByRole('heading', { name: 'Ventas' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Aún no hay actividad para mostrar' })).toHaveCount(0);
      await expect(page.getByText(/Enero 2026: S\/ 750/)).toBeAttached();
    } finally {
      await context.close();
    }
  });

  test('muestra el fallo y recupera la vista con una nueva solicitud', async ({ browser, baseURL }) => {
    const { context, page, state } = await createDashboardContext(browser, baseURL, {
      failRequests: 1,
    });
    try {
      await page.goto('/dashboard');

      await expect(page.getByText(/No pudimos cargar|temporalmente no disponible/i).first()).toBeVisible();
      await page.getByRole('button', { name: 'Reintentar' }).click();
      await expect(page.getByText('Resma API Única')).toBeVisible();
      expect(state.dashboardCalls).toHaveLength(2);
      expect(state.unexpectedRequests).toEqual([]);
    } finally {
      await context.close();
    }
  });

  test('mantiene un estado de carga mientras el endpoint está pendiente', async ({ browser, baseURL }) => {
    const { context, page } = await createDashboardContext(browser, baseURL, { delayMs: 600 });
    try {
      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });

      const dashboardRoot = page.getByTestId('dashboard-business-mockup');
      await expect(dashboardRoot.getByRole('status')).toContainText(/Cargando|Preparando/i);
      await expect(page.getByText('Resma API Única')).toBeVisible();
      await expect(dashboardRoot.getByRole('status')).toHaveCount(0);
    } finally {
      await context.close();
    }
  });
});
