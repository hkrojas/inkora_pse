import { expect, test } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { attachCriticalErrorCollector } from './helpers/assertions';
import { recordsPayload } from './helpers/dashboard-records';
import { chooseInkoraDate, chooseInkoraMonth, chooseInkoraOption, expectPopupWithinViewport, inkoraDayLabel } from './helpers/inkora-controls';

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
    recordsCalls: [],
    unexpectedRequests: [],
  };
  const context = await browser.newContext({
    baseURL,
    viewport: options.viewport || { width: 1280, height: 900 },
    hasTouch: options.hasTouch || false,
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
    if (path === '/analytics/dashboard/business/records' && method === 'GET') {
      state.recordsCalls.push(url);
      const call = state.recordsCalls.length;
      if (options.recordsDelayMs) await new Promise((resolve) => setTimeout(resolve, options.recordsDelayMs));
      if (options.failRecords && call <= options.failRecords) { await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Detalle no disponible' }) }); return; }
      const amount = url.searchParams.get('measure') === 'product' ? url.searchParams.get('product_id') === '912' ? '4568' : '7777' : url.searchParams.get('client_id') === '731' ? '8000' : '12345';
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(options.recordsForQuery ? options.recordsForQuery(url.searchParams) : recordsPayload(url.searchParams, { totalAmount: amount })) });
      return;
    }
    if ((path === '/clientes/search' || path === '/productos/search') && method === 'GET') {
      const clients = path === '/clientes/search';
      const body = clients ? [{ id: 731, razon_social: 'Cliente API Único' }, { id: 732, razon_social: 'Cliente API Dos' }] : [{ id: 911, nombre: 'Resma API Única' }, { id: 912, nombre: 'Tinta API Azul' }];
      const query = (url.searchParams.get('q') || '').toLowerCase();
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body.filter((row) => String(row.razon_social || row.nombre).toLowerCase().includes(query))) });
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

async function recordChartTransitions(page) {
  await page.addInitScript(() => {
    window.__chartMotionEvents = [];
    const seriesIds = new WeakMap();
    let nextId = 0;
    const record = (event) => {
      if (!event.target.classList?.contains('business-chart__series')) return;
      if (!['clip-path', 'opacity'].includes(event.propertyName)) return;
      if (!seriesIds.has(event.target)) seriesIds.set(event.target, ++nextId);
      window.__chartMotionEvents.push({
        type: event.type, property: event.propertyName, elapsed: event.elapsedTime,
        series: seriesIds.get(event.target), time: performance.now(),
        opacity: getComputedStyle(event.target).opacity,
        clipPath: getComputedStyle(event.target).clipPath,
      });
    };
    document.addEventListener('transitionrun', record, true);
    document.addEventListener('transitionend', record, true);
  });
}

async function chartMotionEvents(page) {
  return page.evaluate(() => window.__chartMotionEvents || []);
}

async function waitForChartEntrance(page, completedBefore, properties) {
  await expect.poll(async () => (await chartMotionEvents(page)).filter((event) => event.type === 'transitionend').length).toBe(completedBefore + properties.length);
  const events = await chartMotionEvents(page);
  const ended = events.filter((event) => event.type === 'transitionend').slice(completedBefore);
  expect(ended.map((event) => event.property).sort()).toEqual([...properties].sort());
  expect(ended.every((event) => event.elapsed > 0 && event.elapsed <= 0.3)).toBe(true);
  for (const event of ended) {
    expect(events.some((run) => run.series === event.series && run.type === 'transitionrun' && run.property === event.property)).toBe(true);
  }
  await expect.poll(async () => page.locator('.business-chart__series').evaluate((series) => getComputedStyle(series).opacity)).toBe('1');
  expect(await page.locator('.business-chart__series').evaluate((series) => getComputedStyle(series).clipPath)).toBe('inset(0px)');
  return events;
}

async function afterChartPaint(page) {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function attachChartMotion(page, testInfo, name) {
  const body = JSON.stringify(await chartMotionEvents(page), null, 2);
  await writeFile(testInfo.outputPath(`${name}-transitions.json`), body);
  await testInfo.attach(`${name}: transiciones reales`, { body, contentType: 'application/json' });
  const chart = page.locator('.business-sales');
  if (await chart.count()) {
    const path = testInfo.outputPath(`${name}.png`);
    await chart.screenshot({ path });
    await testInfo.attach(name, { path, contentType: 'image/png' });
  }
}

for (const width of [1440, 390]) {
  test(`animación del gráfico: carga y fechas sin repetir por hover o ampliación a ${width}px`, async ({ browser, baseURL }, testInfo) => {
    const { context, page } = await createDashboardContext(browser, baseURL, { viewport: { width, height: 900 }, payloadForQuery: temporalPayload });
    const errors = attachCriticalErrorCollector(page);
    try {
      await recordChartTransitions(page);
      await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
      await page.goto('/dashboard');
      await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
      const initial = await waitForChartEntrance(page, 0, ['clip-path', 'opacity']);
      await page.locator('.business-chart__hotspot').last().hover();
      await expect(page.getByRole('tooltip')).toBeVisible();
      await expect(page.getByRole('tooltip')).toContainText('S/ 10,000');
      await expect(page.locator('.business-chart__series > g.is-active')).toHaveCount(1);
      await afterChartPaint(page);
      expect(await chartMotionEvents(page)).toEqual(initial);
      await page.getByRole('button', { name: 'Ampliar gráfico', exact: true }).click();
      await expect(page.getByRole('button', { name: 'Reducir gráfico', exact: true })).toHaveAttribute('aria-expanded', 'true');
      await afterChartPaint(page);
      expect(await chartMotionEvents(page)).toEqual(initial);
      await chooseInkoraOption(page, 'Período del resumen', 'Últimos 7 días');
      await expect(page.getByText('Producto 2026-09-23')).toBeVisible();
      const changed = await waitForChartEntrance(page, 2, ['clip-path', 'opacity']);
      expect(new Set(changed.map((event) => event.series)).size).toBe(2);
      expect(await page.locator('.business-chart__hotspot').count()).toBe(7);
      errors.assertClean();
    } finally {
      await attachChartMotion(page, testInfo, `chart-motion-${width}`);
      await context.close();
    }
  });
}

test('animación del gráfico: movimiento reducido conserva solo opacidad', async ({ browser, baseURL }, testInfo) => {
  const { context, page } = await createDashboardContext(browser, baseURL, { payloadForQuery: temporalPayload, reducedMotion: 'reduce' });
  try {
    await recordChartTransitions(page);
    await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
    await page.goto('/dashboard');
    await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
    await waitForChartEntrance(page, 0, ['opacity']);
    await chooseInkoraOption(page, 'Período del resumen', 'Últimos 7 días');
    await expect(page.getByText('Producto 2026-09-23')).toBeVisible();
    const events = await waitForChartEntrance(page, 1, ['opacity']);
    expect(events.every((event) => event.property === 'opacity')).toBe(true);
    expect(events.filter((event) => event.type === 'transitionend').every((event) => event.elapsed <= 0.15)).toBe(true);
  } finally {
    await attachChartMotion(page, testInfo, 'chart-motion-reduced');
    await context.close();
  }
});

test('animación del gráfico: cambiar agrupación con teclado es inmediato', async ({ browser, baseURL }, testInfo) => {
  const { context, page, state } = await createDashboardContext(browser, baseURL, { payloadForQuery: temporalPayload });
  try {
    await recordChartTransitions(page);
    await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
    await page.goto('/dashboard');
    await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
    const initial = await waitForChartEntrance(page, 0, ['clip-path', 'opacity']);
    const grouping = page.getByRole('button', { name: 'Agrupar gráfico', exact: true });
    await grouping.focus();
    await grouping.press('ArrowDown');
    await expect(page.getByRole('listbox', { name: 'Agrupar gráfico', exact: true })).toBeVisible();
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button', { name: 'Consultar mes', exact: true })).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.get('group_by')).toBe('month');
    await afterChartPaint(page);
    expect(await chartMotionEvents(page)).toEqual(initial);
    await expect(page.locator('.business-chart__series')).not.toHaveClass(/business-chart__series--animated/);
    expect(await page.locator('.business-chart__series').evaluate((series) => series.getAnimations().length)).toBe(0);
  } finally {
    await attachChartMotion(page, testInfo, 'chart-motion-keyboard');
    await context.close();
  }
});

for (const mode of ['desktop', 'mobile', 'reduced', 'keyboard']) {
  test(`alternar cotizaciones: transición interrumpible y escala estable (${mode})`, async ({ browser, baseURL }, testInfo) => {
    const { context, page, state } = await createDashboardContext(browser, baseURL, {
      viewport: { width: mode === 'mobile' ? 390 : 1440, height: 900 },
      hasTouch: mode === 'mobile',
      payloadForQuery: variedQuotesPayload,
      reducedMotion: mode === 'reduced' ? 'reduce' : 'no-preference',
    });
    const errors = attachCriticalErrorCollector(page);
    try {
      await page.clock.setFixedTime(new Date('2026-09-30T15:00:00Z'));
      await page.goto('/dashboard');
      const quotes = page.locator('g.business-chart__quoted');
      await expect(quotes).toHaveCSS('opacity', '1');
      await expect(page.locator('.business-chart__series')).toHaveCSS('opacity', '1');
      const salesPath = await page.locator('.business-chart__line--sales').getAttribute('d');
      const calls = state.dashboardCalls.length;
      await quotes.evaluate((element) => {
        window.__quoteToggleEvents = [];
        for (const type of ['transitionrun', 'transitionend', 'transitioncancel']) {
          element.addEventListener(type, (event) => window.__quoteToggleEvents.push({ type, property: event.propertyName, elapsed: event.elapsedTime }));
        }
      });
      const toggle = async () => {
        if (mode === 'keyboard') await page.getByRole('checkbox').press('Space');
        else if (mode === 'mobile') await page.locator('.business-toggle').tap();
        else await page.locator('.business-toggle').click();
      };
      await toggle();
      await expect(quotes).toHaveCSS('opacity', '0');
      await expect(page.locator('.business-chart__legend .business-chart__quoted')).toHaveCSS('opacity', '0');
      await expect(page.locator('.business-chart__line--sales')).toHaveAttribute('d', salesPath);
      await page.locator('.business-chart__hotspot').nth(13).hover();
      await expect(page.getByRole('tooltip')).not.toContainText('Importe cotizado');
      await toggle();
      await expect(quotes).toHaveCSS('opacity', '1');
      if (mode === 'desktop') {
        // Pause halfway to reverse a real transition without racing the test runner.
        await toggle();
        const intermediate = await quotes.evaluate((element) => {
          const animation = element.getAnimations()[0];
          animation.pause();
          animation.currentTime = 110;
          return Number(getComputedStyle(element).opacity);
        });
        expect(intermediate).toBeGreaterThan(0);
        expect(intermediate).toBeLessThan(1);
        await toggle();
        await expect(quotes).toHaveCSS('opacity', '1');
      }
      const events = await page.evaluate(() => window.__quoteToggleEvents);
      if (mode === 'keyboard') expect(events).toEqual([]);
      else {
        const ended = events.filter((event) => event.type === 'transitionend');
        expect(ended.length).toBeGreaterThanOrEqual(2);
        expect(events.every((event) => event.property === 'opacity')).toBe(true);
        expect(ended.every((event) => event.elapsed > 0 && event.elapsed <= (mode === 'reduced' ? 0.15 : 0.22))).toBe(true);
      }
      await expect(page.locator('.business-chart__line--sales')).toHaveAttribute('d', salesPath);
      expect(state.dashboardCalls).toHaveLength(calls);
      await expect(page.locator('.business-chart__point--quoted')).toHaveCount(30);
      const path = testInfo.outputPath(`quote-toggle-${mode}.png`);
      await page.locator('.business-sales').screenshot({ path });
      await testInfo.attach(`Cotizaciones ${mode}`, { path, contentType: 'image/png' });
      const body = JSON.stringify(events, null, 2);
      await testInfo.attach('Transiciones reales', { body, contentType: 'application/json' });
      errors.assertClean();
    } finally {
      await context.close();
    }
  });
}

for (const width of [320, 390, 600, 768, 1024, 1440]) {
  test(`conversión legible: porcentaje decimal sin choques a ${width}px`, async ({ browser, baseURL }, testInfo) => {
    const payload = {
      ...dashboardPayload,
      conversion: { available: true, quote_count: 29, linked_sales_count: 25, rate_percent: '86.2' },
    };
    const { context, page } = await createDashboardContext(browser, baseURL, {
      viewport: { width, height: 900 }, payload, reducedMotion: 'reduce',
    });
    try {
      await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
      await page.goto('/dashboard');
      const conversion = page.locator('.business-sales__conversion');
      await expect(conversion.locator('.business-sales__conversion-rate strong')).toHaveText(/^86[.,]2 %$/);
      await conversion.scrollIntoViewIfNeeded();
      const geometry = await conversion.evaluate((element) => {
        const strong = element.querySelector('.business-sales__conversion-rate strong');
        const label = element.querySelector('.business-sales__conversion-rate span');
        const rate = element.querySelector('.business-sales__conversion-rate');
        const copy = element.querySelector('.business-sales__conversion-copy');
        const range = document.createRange();
        range.selectNodeContents(strong);
        const textRects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0);
        const rect = (node) => {
          const bounds = node.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, right: bounds.right, bottom: bounds.bottom, width: bounds.width, height: bounds.height };
        };
        return {
          percentage: rect(strong), label: rect(label), rate: rect(rate), copy: rect(copy), container: rect(element),
          lines: new Set(textRects.map((bounds) => Math.round(bounds.top * 2) / 2)).size,
          fontSize: parseFloat(getComputedStyle(strong).fontSize),
          lineHeight: parseFloat(getComputedStyle(strong).lineHeight),
          scrollWidth: element.scrollWidth, clientWidth: element.clientWidth,
        };
      });
      expect(geometry.lines).toBe(1);
      expect(geometry.fontSize).toBe(32);
      expect(geometry.percentage.height).toBeLessThanOrEqual(geometry.lineHeight + 1);
      expect(geometry.percentage.right).toBeLessThanOrEqual(geometry.label.x + 1);
      expect(geometry.copy.x >= geometry.rate.right - 1 || geometry.copy.y >= geometry.rate.bottom - 1).toBe(true);
      expect(geometry.percentage.x).toBeGreaterThanOrEqual(geometry.container.x);
      expect(geometry.percentage.right).toBeLessThanOrEqual(geometry.container.right);
      expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth + 1);
      expect(await page.locator('main').evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
      const json = JSON.stringify(geometry, null, 2);
      await writeFile(testInfo.outputPath(`percentage-${width}.json`), json);
      await testInfo.attach(`Porcentaje ${width}px: geometría`, { body: json, contentType: 'application/json' });
      const path = testInfo.outputPath(`percentage-${width}.png`);
      await conversion.screenshot({ path, animations: 'disabled' });
      await testInfo.attach(`Porcentaje ${width}px`, { path, contentType: 'image/png' });
    } finally { await context.close(); }
  });
}

function variedQuotesPayload(params) {
  const payload = temporalPayload(params);
  const daily = [];
  const cursor = new Date(`${payload.meta.period.start}T12:00:00Z`);
  while (cursor.toISOString().slice(0, 10) <= payload.meta.period.end) {
    const index = daily.length;
    const date = cursor.toISOString().slice(0, 10);
    daily.push({
      date, year: cursor.getUTCFullYear(), month: cursor.getUTCMonth() + 1,
      period_start: date, period_end: date, is_partial: false, cutoff_day: null, previous_matched_sales: null,
      sales_amount: String(index % 7 === 0 ? 0 : (index % 5 + 1) * 315),
      quoted_amount: String(index % 4 === 0 ? 0 : (index % 6 + 1) * 227),
    });
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  const monthly = [];
  for (const day of daily) {
    let month = monthly.at(-1);
    if (!month || month.month !== day.month || month.year !== day.year) {
      month = { ...day, date: undefined, sales_amount: 0, quoted_amount: 0 };
      monthly.push(month);
    }
    month.period_end = day.date;
    month.sales_amount += Number(day.sales_amount);
    month.quoted_amount += Number(day.quoted_amount);
  }
  return {
    ...payload,
    conversion: { available: true, quote_count: 29, linked_sales_count: 25, rate_percent: '86.2' },
    history: params.get('group_by') === 'month' ? monthly : daily,
  };
}

function quotedMoney(amount) {
  return `S/ ${new Intl.NumberFormat('es-PE').format(Number(amount))}`;
}

async function quotedDashGeometry(page) {
  return page.locator('.business-chart__line--quoted').evaluate((path) => {
    const length = path.getTotalLength();
    const pathLength = path.hasAttribute('pathLength') ? Number(path.getAttribute('pathLength')) : null;
    const normalization = pathLength ? length / pathLength : 1;
    const scale = path.getScreenCTM().a;
    const declared = getComputedStyle(path).strokeDasharray.split(/[ ,]+/).map(parseFloat);
    return { length, pathLength, declared, effective: declared.map((value) => value * normalization * scale), scale };
  });
}

for (const width of [1440, 390]) {
  test(`cotizaciones diarias: 30 puntos y guiones constantes a ${width}px`, async ({ browser, baseURL }, testInfo) => {
    const { context, page } = await createDashboardContext(browser, baseURL, { viewport: { width, height: 900 }, payloadForQuery: variedQuotesPayload });
    const metrics = {};
    try {
      await recordChartTransitions(page);
      await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
      await page.goto('/dashboard');
      await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
      await waitForChartEntrance(page, 0, ['clip-path', 'opacity']);
      await chooseInkoraOption(page, 'Período del resumen', 'Últimos 30 días');
      await expect(page.getByText('Producto 2026-08-31')).toBeVisible();
      await waitForChartEntrance(page, 2, ['clip-path', 'opacity']);
      await expect(page.locator('.business-chart__point--quoted')).toHaveCount(30);
      await expect(page.locator('.business-chart__point--sales')).toHaveCount(30);
      const daily = variedQuotesPayload(new URLSearchParams({ desde: '2026-08-31', hasta: '2026-09-29', group_by: 'day' })).history;
      for (const index of [0, 1, 14, 29]) {
        await page.locator('.business-chart__hotspot').nth(index).hover();
        const tooltip = page.getByRole('tooltip');
        await expect(tooltip.getByText('Ventas registradas', { exact: false })).toContainText(quotedMoney(daily[index].sales_amount));
        await expect(tooltip.getByText('Importe cotizado', { exact: false })).toContainText(quotedMoney(daily[index].quoted_amount));
      }
      await chooseInkoraOption(page, 'Consultar día', inkoraDayLabel(daily.at(-1).date, 'short'));
      await expect(page.locator('.business-chart__selection')).toContainText(quotedMoney(daily.at(-1).quoted_amount));
      metrics.daily = await quotedDashGeometry(page);
      await page.getByRole('button', { name: 'Ampliar gráfico', exact: true }).click();
      await expect(page.getByRole('button', { name: 'Reducir gráfico', exact: true })).toBeVisible();
      await afterChartPaint(page);
      metrics.expanded = await quotedDashGeometry(page);
      await expect(page.locator('.business-chart__point--quoted')).toHaveCount(30);
      const dailyPath = testInfo.outputPath(`quoted-daily-${width}.png`);
      await page.locator('.business-sales').screenshot({ path: dailyPath });
      await testInfo.attach(`Cotizaciones diarias ${width}px`, { path: dailyPath, contentType: 'image/png' });
      await page.locator('.business-toggle').click();
      await expect(page.getByRole('checkbox')).not.toBeChecked();
      await expect(page.locator('g.business-chart__quoted')).toHaveCSS('opacity', '0');
      await expect(page.locator('.business-chart__point--quoted')).toHaveCount(30);
      await expect(page.locator('.business-chart__point--sales')).toHaveCount(30);
      await expect(page.locator('.business-chart__line--sales')).toHaveCount(1);
      await page.locator('.business-toggle').click();
      await expect(page.getByRole('checkbox')).toBeChecked();
      await expect(page.locator('.business-chart__point--quoted')).toHaveCount(30);
      metrics.restored = await quotedDashGeometry(page);
      await chooseInkoraOption(page, 'Agrupar gráfico', 'Por mes');
      await expect(page.getByRole('button', { name: 'Consultar mes', exact: true })).toBeVisible();
      await waitForChartEntrance(page, 4, ['clip-path', 'opacity']);
      await expect(page.locator('.business-chart__point--quoted')).toHaveCount(2);
      metrics.monthly = await quotedDashGeometry(page);
      for (const value of Object.values(metrics)) {
        expect(value.length).toBeGreaterThan(0);
        expect(value.pathLength).toBeNull();
        expect(value.effective).toHaveLength(2);
        expect(value.effective[0]).toBeCloseTo(6, 1);
        expect(value.effective[1]).toBeCloseTo(4, 1);
      }
      metrics.transitions = await chartMotionEvents(page);
      const path = testInfo.outputPath(`quoted-monthly-${width}.png`);
      await page.locator('.business-sales').screenshot({ path });
      await testInfo.attach(`Cotizaciones por mes ${width}px`, { path, contentType: 'image/png' });
    } finally {
      const body = JSON.stringify(metrics, null, 2);
      await writeFile(testInfo.outputPath(`quoted-metrics-${width}.json`), body);
      await testInfo.attach(`Guiones ${width}px: métricas`, { body, contentType: 'application/json' });
      await context.close();
    }
  });
}

test('fechas sincronizan indicadores, gráfico, productos, clientes y cotizaciones; agrupar conserva el período', async ({ browser, baseURL }) => {
  const { context, page, state } = await createDashboardContext(browser, baseURL, { payloadForQuery: temporalPayload });
  const errors = attachCriticalErrorCollector(page);
  try {
    await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
    await page.goto('/dashboard');
    await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
    await expect(page.getByLabel('Consultar día')).toBeVisible();
    await chooseInkoraOption(page, 'Período del resumen', 'Últimos 7 días');
    await expect(page.getByText('Producto 2026-09-23')).toBeVisible();
    await expect(page.getByText('Cliente 2026-09-23', { exact: true })).toBeVisible();
    await expect(page.getByText('Cotización 2026-09-23', { exact: true })).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 7,000"]')).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 700"]')).toBeVisible();
    expect(await page.locator('.business-chart__hotspot').count()).toBe(7);
    await page.locator('.business-chart__hotspot').last().hover();
    await expect(page.getByRole('tooltip')).toContainText('S/ 7,000');
    await chooseInkoraOption(page, 'Agrupar gráfico', 'Por mes');
    await expect(page.getByLabel('Consultar mes')).toBeVisible();
    await expect(page.locator('.business-chart__hotspot')).toHaveCount(1);
    await expect(page.locator('.business-metric__value [aria-label="S/ 7,000"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.get('desde')).toBe('2026-09-23');
    await chooseInkoraOption(page, 'Período del resumen', 'Mes específico');
    await chooseInkoraMonth(page, 'Mes del resumen', '2026-08');
    await expect(page.getByText('Producto 2026-08-01')).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 8,000"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.get('hasta')).toBe('2026-08-31');
    await chooseInkoraOption(page, 'Período del resumen', 'Todo el historial');
    await expect(page.getByText('Producto 2025-06-17')).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 50,000"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.has('desde')).toBe(false);
    await page.getByRole('button', { name: 'Agrupar gráfico', exact: true }).click();
    await expect(page.getByRole('listbox', { name: 'Agrupar gráfico', exact: true }).getByRole('option', { name: 'Por día', exact: true })).toHaveAttribute('aria-disabled', 'true');
    await page.keyboard.press('Escape');
    await chooseInkoraOption(page, 'Período del resumen', 'Personalizado');
    await chooseInkoraDate(page, 'Desde', '2026-09-20');
    await chooseInkoraDate(page, 'Hasta', '2026-09-10');
    const calls = state.dashboardCalls.length;
    await page.getByRole('button', { name: 'Aplicar fechas' }).click();
    await expect(page.getByRole('alert')).toContainText('La fecha de inicio');
    expect(state.dashboardCalls.length).toBe(calls);
    await chooseInkoraDate(page, 'Desde', '2026-09-10');
    await chooseInkoraDate(page, 'Hasta', '2026-09-11');
    await page.getByRole('button', { name: 'Aplicar fechas' }).click();
    await expect(page.getByText('Producto 2026-09-10')).toBeVisible();
    await expect(page.locator('.business-metric__value [aria-label="S/ 2,000"]')).toBeVisible();
    await chooseInkoraOption(page, 'Consultar día', inkoraDayLabel('2026-09-11', 'short'));
    errors.assertClean();
    await page.getByRole('button', { name: /Ver registros del 11/ }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect.poll(() => state.recordsCalls.at(-1)?.searchParams.get('desde')).toBe('2026-09-11');
    expect(state.recordsCalls.at(-1).searchParams.get('hasta')).toBe('2026-09-11');
  } finally { await context.close(); }
});

for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
  test(`filtros y datos diarios legibles a ${viewport.width}px`, async ({ browser, baseURL }, testInfo) => {
    const { context, page } = await createDashboardContext(browser, baseURL, { viewport, payloadForQuery: temporalPayload, reducedMotion: 'reduce' });
    try {
      await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
      await page.goto('/dashboard');
      await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
      await expect(page.getByTestId('dashboard-business-mockup').locator('select, input[type="date"], input[type="month"]')).toHaveCount(0);
      await page.getByRole('button', { name: 'Período del resumen', exact: true }).click();
      await expectPopupWithinViewport(page, page.getByRole('listbox', { name: 'Período del resumen', exact: true }));
      await page.keyboard.press('Escape');
      await chooseInkoraOption(page, 'Período del resumen', 'Últimos 7 días');
      await expect(page.getByText('Producto 2026-09-23')).toBeVisible();
      const overflow = await page.locator('main').evaluate((element) => element.scrollWidth > element.clientWidth + 1);
      expect(overflow).toBe(false);
      await chooseInkoraOption(page, 'Consultar día', inkoraDayLabel('2026-09-29', 'short'));
      await expect(page.locator('.business-chart__selection')).toContainText('S/ 7,000');
      const screenshot = testInfo.outputPath(`dashboard-filters-${viewport.width}.png`);
      await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
      await testInfo.attach(`Filtros ${viewport.width}px`, { path: screenshot, contentType: 'image/png' });
      const chartScreenshot = testInfo.outputPath(`dashboard-chart-${viewport.width}.png`);
      await page.locator('.business-sales').screenshot({ path: chartScreenshot, animations: 'disabled' });
      await testInfo.attach(`Gráfico ${viewport.width}px`, { path: chartScreenshot, contentType: 'image/png' });
      await chooseInkoraOption(page, 'Período del resumen', 'Personalizado');
      await expect(page.getByRole('button', { name: 'Aplicar fechas' })).toBeVisible();
      expect(await page.locator('main').evaluate((element) => element.scrollWidth > element.clientWidth + 1)).toBe(false);
      const dateTrigger = page.getByRole('button', { name: 'Hasta', exact: true });
      await dateTrigger.click();
      const calendar = page.getByRole('dialog', { name: 'Seleccionar fecha', exact: true });
      await expectPopupWithinViewport(page, calendar);
      await expect(calendar.getByRole('button', { name: inkoraDayLabel('2026-09-30'), exact: true })).toBeDisabled();
      const calendarScreenshot = testInfo.outputPath(`dashboard-calendar-${viewport.width}.png`);
      await page.screenshot({ path: calendarScreenshot, animations: 'disabled' });
      await testInfo.attach(`Calendario de Inkora ${viewport.width}px`, { path: calendarScreenshot, contentType: 'image/png' });
      await page.keyboard.press('Escape');
      await expect(dateTrigger).toBeFocused();
      await chooseInkoraOption(page, 'Período del resumen', 'Mes específico');
      await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
      await page.getByRole('button', { name: 'Mes del resumen', exact: true }).click();
      const monthCalendar = page.getByRole('dialog', { name: 'Seleccionar mes', exact: true });
      await expectPopupWithinViewport(page, monthCalendar);
      await expect(monthCalendar.getByRole('button', { name: 'Octubre 2026', exact: true })).toBeDisabled();
      const monthScreenshot = testInfo.outputPath(`dashboard-month-${viewport.width}.png`);
      await page.screenshot({ path: monthScreenshot, animations: 'disabled' });
      await testInfo.attach(`Meses de Inkora ${viewport.width}px`, { path: monthScreenshot, contentType: 'image/png' });
      await page.keyboard.press('Escape');
    } finally { await context.close(); }
  });
}

test('los selectores de Inkora admiten teclado y respetan las opciones deshabilitadas', async ({ browser, baseURL }) => {
  const { context, page, state } = await createDashboardContext(browser, baseURL, { payloadForQuery: temporalPayload, reducedMotion: 'reduce' });
  const errors = attachCriticalErrorCollector(page);
  try {
    await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
    await page.goto('/dashboard');
    await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
    const period = page.getByRole('button', { name: 'Período del resumen', exact: true });
    await period.focus();
    await period.press('ArrowDown');
    await expect(page.getByRole('listbox', { name: 'Período del resumen', exact: true })).toBeVisible();
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await expect(page.getByText('Producto 2026-09-23')).toBeVisible();
    await expect(period).toContainText('Últimos 7 días');
    await chooseInkoraOption(page, 'Período del resumen', 'Todo el historial');
    await expect(page.getByText('Producto 2025-06-17')).toBeVisible();
    const group = page.getByRole('button', { name: 'Agrupar gráfico', exact: true });
    await group.focus();
    await group.press('ArrowUp');
    const listbox = page.getByRole('listbox', { name: 'Agrupar gráfico', exact: true });
    await expect(listbox.getByRole('option', { name: 'Por día', exact: true })).toHaveAttribute('aria-disabled', 'true');
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('Enter');
    await expect(group).toContainText('Por mes');
    await expect(listbox).toHaveCount(0);
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.get('group_by')).toBe('month');
    await group.click();
    await page.keyboard.press('Escape');
    await expect(group).toBeFocused();
    await chooseInkoraOption(page, 'Período del resumen', 'Mes específico');
    const month = page.getByRole('button', { name: 'Mes del resumen', exact: true });
    await month.click();
    await expect(page.getByRole('dialog', { name: 'Seleccionar mes', exact: true }).getByRole('button', { name: 'Septiembre 2026', exact: true })).toBeFocused();
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('Enter');
    await expect(page.getByText('Producto 2026-08-01')).toBeVisible();
    await expect(month).toContainText('Agosto 2026');
    await chooseInkoraOption(page, 'Período del resumen', 'Personalizado');
    const until = page.getByRole('button', { name: 'Hasta', exact: true });
    await until.click();
    await expect(page.getByRole('dialog', { name: 'Seleccionar fecha', exact: true }).getByRole('button', { name: inkoraDayLabel('2026-09-29'), exact: true })).toBeFocused();
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('Enter');
    await expect(until).toContainText('28/09/2026');
    errors.assertClean();
  } finally { await context.close(); }
});

for (const width of [320, 390, 600, 768, 1024, 1440]) {
  test(`anchos de controles: opciones completas y una línea a ${width}px`, async ({ browser, baseURL }, testInfo) => {
    const { context, page } = await createDashboardContext(browser, baseURL, {
      viewport: { width, height: 900 }, payloadForQuery: temporalPayload, reducedMotion: 'reduce',
    });
    const geometry = [];
    const inspectMenu = async (label) => {
      await page.getByRole('button', { name: label, exact: true }).click();
      const popup = page.getByRole('listbox', { name: label, exact: true });
      await expect(popup).toBeVisible();
      await expect.poll(async () => (await popup.boundingBox())?.width || 0).toBeGreaterThan(80);
      const rows = await popup.getByRole('option').evaluateAll((options) => options.map((option) => {
        const bounds = option.getBoundingClientRect();
        const walker = document.createTreeWalker(option, NodeFilter.SHOW_TEXT);
        const textRects = [];
        let node;
        while ((node = walker.nextNode())) {
          if (!node.textContent.trim()) continue;
          const range = document.createRange();
          range.selectNodeContents(node);
          textRects.push(...Array.from(range.getClientRects()).filter((rect) => rect.width > 0 && rect.height > 0));
        }
        return {
          label: option.textContent.trim(),
          lines: new Set(textRects.map((rect) => Math.round(rect.top * 2) / 2)).size,
          textFits: textRects.every((rect) => rect.left >= bounds.left - 1 && rect.right <= bounds.right + 1),
          width: bounds.width,
          height: bounds.height,
          rects: textRects.map((rect) => ({ x: rect.x, y: rect.y, width: rect.width, height: rect.height })),
        };
      }));
      geometry.push({ control: label, popup: await popup.boundingBox(), options: rows });
      for (const row of rows) {
        expect.soft(row.lines, `${label}: «${row.label}» ocupa más de una línea a ${width}px`).toBe(1);
        expect.soft(row.textFits, `${label}: «${row.label}» se corta a ${width}px`).toBe(true);
      }
      await expectPopupWithinViewport(page, popup);
      expect.soft(await popup.evaluate((element) => element.scrollWidth <= element.clientWidth + 1), `${label}: desbordamiento horizontal`).toBe(true);
      const screenshot = testInfo.outputPath(`control-${label.replaceAll(' ', '-')}-${width}.png`);
      await page.screenshot({ path: screenshot, animations: 'disabled' });
      await testInfo.attach(`${label} ${width}px`, { path: screenshot, contentType: 'image/png' });
      await page.keyboard.press('Escape');
    };
    try {
      await page.clock.setFixedTime(new Date('2026-09-29T15:00:00Z'));
      await page.goto('/dashboard');
      await expect(page.getByText('Producto 2026-09-01')).toBeVisible();
      await inspectMenu('Período del resumen');
      await inspectMenu('Agrupar gráfico');
      await inspectMenu('Consultar día');
      await inspectMenu('Ordenar productos');
      await chooseInkoraOption(page, 'Período del resumen', 'Mes específico');
      await page.getByRole('button', { name: 'Mes del resumen', exact: true }).click();
      const months = page.getByRole('dialog', { name: 'Seleccionar mes', exact: true });
      await expectPopupWithinViewport(page, months);
      geometry.push({
        control: 'Calendario de meses',
        popup: await months.boundingBox(),
        options: await months.locator('.ink-date-day').evaluateAll((buttons) => buttons.map((button) => {
          const bounds = button.getBoundingClientRect();
          const range = document.createRange();
          range.selectNodeContents(button);
          const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0);
          return { label: button.textContent.trim(), width: bounds.width, textWidth: Math.max(...rects.map((rect) => rect.width)), textFits: rects.every((rect) => rect.left >= bounds.left - 1 && rect.right <= bounds.right + 1) };
        })),
      });
      for (const month of geometry.at(-1).options) expect.soft(month.textFits, `Mes «${month.label}» se corta a ${width}px`).toBe(true);
      const monthScreenshot = testInfo.outputPath(`calendario-meses-${width}.png`);
      await page.screenshot({ path: monthScreenshot, animations: 'disabled' });
      await testInfo.attach(`Meses ${width}px`, { path: monthScreenshot, contentType: 'image/png' });
      await page.keyboard.press('Escape');
      await chooseInkoraOption(page, 'Período del resumen', 'Personalizado');
      for (const label of ['Desde', 'Hasta']) {
        const trigger = page.getByRole('button', { name: label, exact: true });
        const bounds = await trigger.evaluate((button) => {
          const rect = button.getBoundingClientRect();
          const range = document.createRange();
          range.selectNodeContents(button.querySelector('span'));
          const text = range.getBoundingClientRect();
          const icon = button.querySelector('svg').getBoundingClientRect();
          return {
            width: rect.width,
            textFits: text.left >= rect.left - 1 && text.right <= rect.right + 1,
            iconFits: icon.left >= rect.left - 1 && icon.right <= rect.right + 1,
            textIconOverlap: text.right > icon.left,
            scrollWidth: button.scrollWidth,
            clientWidth: button.clientWidth,
          };
        });
        geometry.push({ control: label, trigger: bounds });
        expect.soft(bounds.textFits && bounds.iconFits, `${label}: fecha o icono fuera del botón a ${width}px`).toBe(true);
        expect.soft(bounds.textIconOverlap, `${label}: fecha e icono se superponen a ${width}px`).toBe(false);
        expect.soft(bounds.scrollWidth <= bounds.clientWidth + 1, `${label}: desbordamiento interno a ${width}px`).toBe(true);
      }
      await page.getByRole('button', { name: 'Hasta', exact: true }).click();
      await expectPopupWithinViewport(page, page.getByRole('dialog', { name: 'Seleccionar fecha', exact: true }));
      await page.keyboard.press('Escape');
      expect.soft(await page.locator('main').evaluate((element) => element.scrollWidth <= element.clientWidth + 1), `Resumen: desbordamiento horizontal a ${width}px`).toBe(true);
    } finally {
      const geometryPath = testInfo.outputPath(`control-geometry-${width}.json`);
      await writeFile(geometryPath, JSON.stringify(geometry, null, 2));
      await testInfo.attach(`Geometría controles ${width}px`, { path: geometryPath, contentType: 'application/json' });
      await context.close();
    }
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
    await chooseInkoraOption(page, 'Período del resumen', 'Últimos 7 días');
    await chooseInkoraOption(page, 'Período del resumen', 'Todo el historial');
    await expect(page.getByText('Producto 2025-06-17')).toBeVisible();
    // Wait for the slower obsolete response, then prove it did not replace the current one.
    await page.waitForTimeout(750);
    await expect(page.getByText('Producto 2025-06-17')).toBeVisible();
    await expect(page.getByText('Producto 2026-09-23')).toHaveCount(0);
  } finally { await context.close(); }
});

test('paneles de producto, cliente y gráfico conservan filtros, totales y paginación sin abandonar el resumen', async ({ browser, baseURL }) => {
  const { context, page, state } = await createDashboardContext(browser, baseURL, { reducedMotion: 'reduce' });
  try {
    await page.goto('/dashboard');
    const product = page.getByRole('button', { name: 'Resma API Única', exact: true });
    await product.click();
    const panel = page.getByRole('dialog', { name: 'Ventas de Resma API Única' });
    await expect(panel).toBeVisible();
    await expect(panel.locator('.business-explorer__total')).toContainText('S/ 7,777');
    await expect(page).toHaveURL(/\/dashboard$/);
    const productQuery = state.recordsCalls.at(-1).searchParams;
    expect(productQuery.get('measure')).toBe('product');
    expect(productQuery.get('product_id')).toBe('911');
    expect(productQuery.get('product_unit')).toBe('NIU');
    expect(productQuery.get('desde')).toBe('2026-09-01');
    expect(productQuery.get('hasta')).toBe('2026-09-28');
    await expect(panel.getByText('Página 1 de 2.', { exact: false })).toBeVisible();
    await expect(panel.getByRole('button', { name: 'Anterior' })).toBeDisabled();
    await panel.getByRole('button', { name: 'Siguiente' }).click();
    await expect(panel.getByRole('button', { name: 'F001-000016', exact: true })).toBeVisible();
    await expect(panel.locator('.business-explorer__total')).toContainText('S/ 7,777');
    expect(state.recordsCalls.at(-1).searchParams.get('skip')).toBe('15');
    await expect(panel.getByRole('button', { name: 'Siguiente' })).toBeDisabled();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(product).toBeFocused();
    await page.getByRole('button', { name: 'Cliente API Único', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Compras de Cliente API Único' })).toBeVisible();
    await expect(page.locator('.business-explorer__total')).toContainText('S/ 8,000');
    expect(state.recordsCalls.at(-1).searchParams.get('client_id')).toBe('731');
    expect(state.recordsCalls.at(-1).searchParams.get('measure')).toBe('document');
    await page.locator('.business-explorer').click({ position: { x: 10, y: 10 } });
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await page.getByRole('button', { name: /Septiembre 2026: ventas/ }).click();
    await expect(page.getByRole('dialog', { name: 'Ventas de Septiembre 2026' })).toBeVisible();
    await expect(page.locator('.business-explorer__total')).toContainText('S/ 12,345');
    expect(state.recordsCalls.at(-1).searchParams.get('hasta')).toBe('2026-09-28');
    await page.getByRole('button', { name: 'Cerrar detalle' }).click();
    expect(state.unexpectedRequests).toEqual([]);
    // A specific record, rather than its product/client catalog, is the drill-through.
    await product.click();
    await page.getByRole('button', { name: 'F001-000001', exact: true }).click();
    await expect(page).toHaveURL(/\/cotizaciones\/9000$/);
  } finally { await context.close(); }
});

test('los filtros de cliente y producto buscan, recalculan y se conservan en las ventanas', async ({ browser, baseURL }) => {
  const { context, page, state } = await createDashboardContext(browser, baseURL, {
    reducedMotion: 'reduce',
    payloadForQuery: (params) => ({
      ...dashboardPayload,
      meta: { ...dashboardPayload.meta, client_id: params.get('client_id'), product_id: params.get('product_id') },
      summary: { ...dashboardPayload.summary, sales_amount: params.has('client_id') && params.has('product_id') ? '3500' : params.has('client_id') ? '8000' : '12345' },
    }),
  });
  try {
    await page.goto('/dashboard');
    await expect(page.getByText('Resma API Única')).toBeVisible();
    await page.getByRole('button', { name: 'Filtrar por cliente' }).click();
    await page.getByRole('textbox', { name: 'Buscar cliente' }).fill('Cliente API Único');
    await page.getByRole('option', { name: 'Cliente API Único', exact: true }).click();
    await expect(page.locator('.business-metric__value [aria-label="S/ 8,000"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.get('client_id')).toBe('731');
    await page.getByRole('button', { name: 'Filtrar por producto' }).click();
    await page.getByRole('textbox', { name: 'Buscar producto' }).fill('Resma');
    await page.getByRole('option', { name: 'Resma API Única', exact: true }).click();
    await expect(page.locator('.business-metric__value [aria-label="S/ 3,500"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.get('product_id')).toBe('911');
    await expect(page.getByText(/Las tarjetas, el gráfico y los clientes muestran el total/)).toBeVisible();
    await page.getByRole('button', { name: 'Tinta API Azul', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Ventas de Tinta API Azul' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'F001-000001', exact: true })).toBeVisible();
    const query = state.recordsCalls.at(-1).searchParams;
    expect(query.get('product_id')).toBe('912');
    expect(query.get('contains_product_id')).toBe('911');
    expect(query.get('client_id')).toBe('731');
    await page.getByRole('button', { name: 'Cerrar detalle' }).click();
    await page.getByRole('button', { name: 'Limpiar cliente y producto' }).click();
    await expect(page.locator('.business-metric__value [aria-label="S/ 12,345"]')).toBeVisible();
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.has('client_id')).toBe(false);
    expect(new URL(state.dashboardCalls.at(-1).url).searchParams.has('product_id')).toBe(false);
    expect(state.unexpectedRequests).toEqual([]);
  } finally { await context.close(); }
});

test('detalle distingue carga, error recuperable y registros vacíos', async ({ browser, baseURL }) => {
  const { context, page } = await createDashboardContext(browser, baseURL, {
    recordsDelayMs: 400, failRecords: 1,
    recordsForQuery: (params) => recordsPayload(params, { total: 0, totalAmount: '0' }),
  });
  try {
    await page.goto('/dashboard');
    await page.getByRole('button', { name: 'Resma API Única', exact: true }).click();
    await expect(page.getByRole('dialog').getByRole('status')).toContainText('Cargando registros');
    await expect(page.getByRole('dialog').getByRole('alert')).toContainText('No pudimos cargar');
    await page.getByRole('dialog').getByRole('button', { name: 'Reintentar' }).click();
    await expect(page.getByText('No hay ventas registradas con estos filtros.')).toBeVisible();
    await expect(page.locator('.business-explorer__total')).toContainText('S/ 0');
    await expect(page.getByRole('button', { name: 'F001-000001', exact: true })).toHaveCount(0);
  } finally { await context.close(); }
});

for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
  test(`ventana aprobada y filtros sin desbordamiento a ${viewport.width}px`, async ({ browser, baseURL }) => {
    const { context, page } = await createDashboardContext(browser, baseURL, { viewport, reducedMotion: 'reduce' });
    try {
      await page.goto('/dashboard');
      await page.getByRole('button', { name: 'Filtrar por producto' }).click();
      await expect(page.getByRole('listbox')).toBeVisible();
      const dropdown = await page.getByRole('listbox').boundingBox();
      expect(dropdown.x).toBeGreaterThanOrEqual(0);
      expect(dropdown.x + dropdown.width).toBeLessThanOrEqual(viewport.width);
      await page.keyboard.press('Escape');
      await page.getByRole('button', { name: 'Resma API Única', exact: true }).click();
      const panel = page.getByRole('dialog');
      await expect(panel.getByRole('button', { name: 'F001-000001', exact: true })).toBeVisible();
      expect(await panel.evaluate((element) => element.scrollWidth > element.clientWidth + 1)).toBe(false);
      expect(await page.locator('main').evaluate((element) => element.scrollWidth > element.clientWidth + 1)).toBe(false);
      await expect(page.getByRole('button', { name: 'Cerrar detalle' })).toBeFocused();
      await page.keyboard.press('Shift+Tab');
      await expect(panel.getByRole('button', { name: 'Siguiente' })).toBeFocused();
      const paginationColors = await panel.getByRole('button', { name: 'Siguiente' }).evaluate((element) => ({ background: getComputedStyle(element).backgroundColor, color: getComputedStyle(element).color }));
      expect(paginationColors.background).not.toBe('rgba(0, 0, 0, 0)');
      expect(paginationColors.background).not.toBe(paginationColors.color);
      await page.keyboard.press('Tab');
      await expect(page.getByRole('button', { name: 'Cerrar detalle' })).toBeFocused();
      await page.screenshot({ path: `test-results/dashboard-explorer-${viewport.width}.png`, animations: 'disabled' });
      await page.getByRole('button', { name: 'Cerrar detalle' }).click();
      await expect(page.getByRole('button', { name: 'Resma API Única', exact: true })).toBeFocused();
    } finally { await context.close(); }
  });
}
