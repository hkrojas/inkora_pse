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
    reducedMotion: options.reducedMotion || 'no-preference',
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
      if (options.delayMs) await new Promise((resolve) => setTimeout(resolve, typeof options.delayMs === 'function' ? options.delayMs(url.searchParams) : options.delayMs));
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
        body: JSON.stringify(options.payloadForQuery ? options.payloadForQuery(url.searchParams) : options.payload || dashboardPayload),
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
      await expect(page.getByRole('heading', { name: 'No hay actividad en estas fechas' })).toBeVisible();
      await expect(page.getByText('Prueba otro período o consulta Todo el historial.')).toBeVisible();
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
      await expect(page.getByRole('heading', { name: 'No hay actividad en estas fechas' })).toHaveCount(0);
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

function temporalPayload(params) {
  const all = params.get('period_scope') === 'all';
  const start = all ? '2025-06-17' : params.get('desde');
  const end = all ? '2026-09-29' : params.get('hasta');
  const group = params.get('group_by');
  const amount = all ? 50000 : start === '2026-09-23' ? 7000 : start === '2026-08-01' ? 8000 : start === '2026-09-10' ? 2000 : 10000;
  const history = [];
  let cursor = new Date(`${start}T00:00:00Z`);
  if (group === 'month') cursor.setUTCDate(1);
  while (cursor.toISOString().slice(0, 10) <= end) {
    const date = cursor.toISOString().slice(0, 10);
    const last = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 0)).toISOString().slice(0, 10);
    history.push({
      year: cursor.getUTCFullYear(), month: cursor.getUTCMonth() + 1,
      ...(group === 'day' ? { date } : {}),
      period_start: date < start ? start : date,
      period_end: group === 'day' ? date : last > end ? end : last,
      sales_amount: '0', quoted_amount: '0', is_partial: group === 'month' && (date < start || last > end),
      cutoff_day: Number(end.slice(-2)), previous_matched_sales: null,
    });
    if (group === 'day') cursor.setUTCDate(cursor.getUTCDate() + 1);
    else cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
  history.at(-1).sales_amount = String(amount);
  history.at(-1).quoted_amount = String(amount + 1000);
  return {
    ...dashboardPayload,
    meta: { ...dashboardPayload.meta, period: { start, end }, history: { start, end }, group_by: group, history_scope: 'period', period_scope: all ? 'all' : 'selected' },
    summary: { ...dashboardPayload.summary, sales_amount: String(amount), average_sale: String(amount / 3), overdue_amount: String(amount / 10) },
    history,
    conversion: { available: true, quote_count: 4, linked_sales_count: 1, rate_percent: '25' },
    products: [{ ...dashboardPayload.products[0], name: `Producto ${start}`, amount: String(amount) }],
    clients: [{ ...dashboardPayload.clients[0], name: `Cliente ${start}`, amount: String(amount), share_percent: '100' }],
    follow_up: { ...dashboardPayload.follow_up, quotes: { available: true, count: 3, rows: [{ quote_id: 300, client_id: 733, client: `Cotización ${start}`, reference: 'COT-000300', amount: '800', age_days: 6 }] } },
  };
}

test('fechas sincronizan indicadores, gráfico, productos, clientes y cotizaciones; agrupar conserva el período', async ({ browser, baseURL }) => {
  const { context, page, state } = await createDashboardContext(browser, baseURL, { payloadForQuery: temporalPayload });
  const errors = attachCriticalErrorCollector(page);
  try {
    await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
    await page.goto('/dashboard');
    await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
    await expect(page.getByLabel('Consultar día')).toBeVisible();
    await page.getByLabel('Período del resumen').selectOption('week');
    await expect(page.getByText('Producto 2026-09-23')).toBeVisible();
    await expect(page.getByText('Cliente 2026-09-23', { exact: true })).toBeVisible();
    await expect(page.getByText('Cotización 2026-09-23', { exact: true })).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 7,000"]')).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 700"]')).toBeVisible();
    expect(await page.locator('.business-chart__hotspot').count()).toBe(7);
    await page.locator('.business-chart__hotspot').last().hover();
    await expect(page.getByRole('tooltip')).toContainText('S/ 7,000');
    await page.getByLabel('Agrupar gráfico').selectOption('month');
    await expect(page.getByLabel('Consultar mes')).toBeVisible();
    await expect(page.locator('.business-chart__hotspot')).toHaveCount(1);
    await expect(page.locator('.business-metric__value [aria-label="S/ 7,000"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.get('desde')).toBe('2026-09-23');
    await page.getByLabel('Período del resumen').selectOption('month');
    await page.getByLabel('Mes del resumen').fill('2026-08');
    await expect(page.getByText('Producto 2026-08-01')).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 8,000"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.get('hasta')).toBe('2026-08-31');
    await page.getByLabel('Período del resumen').selectOption('all');
    await expect(page.getByText('Producto 2025-06-17')).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 50,000"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.has('desde')).toBe(false);
    await expect(page.getByLabel('Agrupar gráfico').locator('option[value="day"]')).toHaveAttribute('disabled', '');
    await page.getByLabel('Período del resumen').selectOption('custom');
    await page.getByLabel('Desde', { exact: true }).fill('2026-09-20');
    await page.getByLabel('Hasta', { exact: true }).fill('2026-09-10');
    const calls = state.dashboardCalls.length;
    await page.getByRole('button', { name: 'Aplicar fechas' }).click();
    await expect(page.getByRole('alert')).toContainText('La fecha de inicio');
    expect(state.dashboardCalls.length).toBe(calls);
    await page.getByLabel('Desde', { exact: true }).fill('2026-09-10');
    await page.getByLabel('Hasta', { exact: true }).fill('2026-09-11');
    await page.getByRole('button', { name: 'Aplicar fechas' }).click();
    await expect(page.getByText('Producto 2026-09-10')).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 2,000"]')).toBeVisible();
    await page.getByLabel('Consultar día').selectOption('1');
    errors.assertClean();
    await page.getByRole('button', { name: /Ver registros del 11/ }).click();
    await expect(page).toHaveURL(/desde=2026-09-11&hasta=2026-09-11/);
  } finally { await context.close(); }
});

for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
  test(`filtros y datos diarios legibles a ${viewport.width}px`, async ({ browser, baseURL }, testInfo) => {
    const { context, page } = await createDashboardContext(browser, baseURL, { viewport, payloadForQuery: temporalPayload, reducedMotion: 'reduce' });
    try {
      await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
      await page.goto('/dashboard');
      await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
      await page.getByLabel('Período del resumen').selectOption('week');
      await expect(page.getByText('Producto 2026-09-23')).toBeVisible();
      const overflow = await page.locator('main').evaluate((element) => element.scrollWidth > element.clientWidth + 1);
      expect(overflow).toBe(false);
      await page.getByLabel('Consultar día').selectOption('6');
      await expect(page.locator('.business-chart__selection')).toContainText('S/ 7,000');
      const screenshot = testInfo.outputPath(`dashboard-filters-${viewport.width}.png`);
      await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
      await testInfo.attach(`Filtros ${viewport.width}px`, { path: screenshot, contentType: 'image/png' });
      const chartScreenshot = testInfo.outputPath(`dashboard-chart-${viewport.width}.png`);
      await page.locator('.business-sales').screenshot({ path: chartScreenshot, animations: 'disabled' });
      await testInfo.attach(`Gráfico ${viewport.width}px`, { path: chartScreenshot, contentType: 'image/png' });
      await page.getByLabel('Período del resumen').selectOption('custom');
      await expect(page.getByRole('button', { name: 'Aplicar fechas' })).toBeVisible();
      expect(await page.locator('main').evaluate((element) => element.scrollWidth > element.clientWidth + 1)).toBe(false);
    } finally { await context.close(); }
  });
}

test('al cambiar fechas rápidamente la última selección conserva sus datos', async ({ browser, baseURL }) => {
  const { context, page } = await createDashboardContext(browser, baseURL, {
    payloadForQuery: temporalPayload,
    delayMs: (params) => params.get('desde') === '2026-09-23' ? 600 : 0,
  });
  try {
    await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
    await page.goto('/dashboard');
    await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
    await page.getByLabel('Período del resumen').selectOption('week');
    await page.getByLabel('Período del resumen').selectOption('all');
    await expect(page.getByText('Producto 2025-06-17')).toBeVisible();
    // Wait for the slower obsolete response, then prove it did not replace the current one.
    await page.waitForTimeout(750);
    await expect(page.getByText('Producto 2025-06-17')).toBeVisible();
    await expect(page.getByText('Producto 2026-09-23')).toHaveCount(0);
  } finally { await context.close(); }
});
