import { expect, test } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const debtRows = () => Array.from({ length: 67 }, (_, index) => ({
  cotizacion_id: index + 1,
  cliente_nombre: index === 66 ? 'Comercial Histórico Fuera de los Primeros Cincuenta' : `Cliente ${String(index + 1).padStart(3, '0')}`,
  document_number: `F001-${String(index + 1).padStart(6, '0')}`,
  dias_vencido: [40, 5, 0, -3][index % 4], fecha_vencimiento: '2026-09-01T12:00:00', saldo_pendiente: 100,
}));
const returnRows = () => Array.from({ length: 37 }, (_, index) => ({
  id: index + 1, credit_note_id: index + 1, credit_note_number: `NC-${String(index + 1).padStart(3, '0')}`, status: 'pending',
  items: [{ id: index + 1, product_name: `Producto devuelto ${index + 1}`, authorized_quantity: 2, received_quantity: 0 }],
}));
const matchesSegment = (item, segment) => segment === 'vencidos' ? item.dias_vencido > 0
  : segment === 'criticos' ? item.dias_vencido > 30 : segment === 'hoy' ? item.dias_vencido === 0
    : segment === 'proximos' ? item.dias_vencido < 0 : true;

async function openOperationalPage(browser, baseURL, width, path, { debtCount = 67 } = {}) {
  const context = await browser.newContext({ baseURL, viewport: { width, height: 960 }, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
  await context.addInitScript(() => localStorage.setItem('token', 'operational-pagination-e2e-token'));
  const page = await context.newPage();
  const state = { debts: debtRows().slice(0, debtCount), returns: returnRows(), calls: [], mutations: [], unexpected: [], heldSearch: null };
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const endpoint = url.pathname.replace(/\/$/, '');
    state.calls.push({ endpoint, params: Object.fromEntries(url.searchParams) });
    let payload;
    if (request.method() === 'POST' && /^\/cotizaciones\/\d+\/pagos$/.test(endpoint)) {
      state.mutations.push(endpoint);
      const id = Number(endpoint.split('/')[2]);
      state.debts = state.debts.filter((item) => item.cotizacion_id !== id);
      payload = {};
    } else if (request.method() === 'POST' && /^\/inventario\/devoluciones\/\d+\/recibir$/.test(endpoint)) {
      state.mutations.push(endpoint);
      const item = state.returns.find((row) => row.id === Number(endpoint.split('/')[3]));
      item.status = 'received';
      item.items[0].received_quantity = 2;
      payload = item;
    } else if (request.method() !== 'GET') state.unexpected.push(`${request.method()} ${endpoint}`);
    else if (endpoint === '/users/me') payload = { id: 7301, email: 'pages.e2e@inkora.test', nombre_completo: 'Operador Páginas', rol: 'admin', is_superadmin: false, must_change_password: false, tenant_id: 73 };
    else if (endpoint === '/tenant/subscription-status') payload = { fiscal_feature_flags: {} };
    else if (endpoint === '/sunat/exchange-rate') payload = { compra: 3.7, venta: 3.72, moneda: 'USD' };
    else if (endpoint === '/cobranza/resumen') payload = { total_por_cobrar: 6700, documentos_vencidos: 34, total_pagado_mes: 2300 };
    else if (endpoint === '/cobranza/vencidas/page') {
      const q = (url.searchParams.get('q') || '').toLowerCase();
      const base = state.debts.filter((row) => !q || `${row.cliente_nombre} ${row.document_number}`.toLowerCase().includes(q));
      const counts = Object.fromEntries(['all', 'vencidos', 'criticos', 'hoy', 'proximos'].map((segment) => [segment, base.filter((row) => matchesSegment(row, segment)).length]));
      const rows = base.filter((row) => matchesSegment(row, url.searchParams.get('segment')));
      const skip = Number(url.searchParams.get('skip') || 0);
      const limit = Number(url.searchParams.get('limit'));
      payload = { items: rows.slice(skip, skip + limit), total: rows.length, counts, skip, limit };
      if (state.heldSearch?.query === q) {
        state.heldSearch.started();
        await state.heldSearch.wait;
      }
    } else if (endpoint === '/inventario/devoluciones/page') {
      const skip = Number(url.searchParams.get('skip') || 0);
      const limit = Number(url.searchParams.get('limit'));
      payload = { items: state.returns.slice(skip, skip + limit), total: state.returns.length, skip, limit };
    } else if (endpoint === '/inventario/existencias') payload = [{ product_id: 1, product_name: 'Papel', warehouse_id: 1, warehouse_name: 'Principal', status: 'ok', on_hand: 20, committed: 0, available: 20, unit: 'NIU' }];
    else if (endpoint === '/inventario/kardex/page') payload = { items: [], total: 0, skip: 0, limit: 15 };
    else if (endpoint === '/inventario/almacenes') payload = [{ id: 1, name: 'Principal', is_active: true }];
    else if (endpoint === '/inventario/establecimientos-fiscales') payload = [];
    else state.unexpected.push(`${request.method()} ${endpoint}`);
    await route.fulfill({ status: payload === undefined ? 500 : 200, contentType: 'application/json', body: JSON.stringify(payload ?? { detail: 'Solicitud no simulada' }) });
  });
  const errors = attachCriticalErrorCollector(page);
  await page.goto(path);
  return { context, page, state, errors };
}

async function assertViewportAndCapture(page, testInfo, label) {
  // The app shell scrolls independently of the document: fullPage alone can
  // capture the header while leaving the list footer outside the viewport.
  await page.locator('.pagination').last().scrollIntoViewIfNeeded();
  const geometry = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth,
    pagination: [...document.querySelectorAll('.pagination')].map((element) => { const r = element.getBoundingClientRect(); return { left: r.left, right: r.right }; }) }));
  expect(geometry.scroll).toBeLessThanOrEqual(geometry.viewport);
  geometry.pagination.forEach((rect) => { expect(rect.left).toBeGreaterThanOrEqual(0); expect(rect.right).toBeLessThanOrEqual(geometry.viewport); });
  await testInfo.attach(`${label}-geometry`, { body: JSON.stringify(geometry, null, 2), contentType: 'application/json' });
  const path = testInfo.outputPath(`${label}.png`);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(label, { path, contentType: 'image/png' });
}

for (const width of [1440, 390]) {
  test(`cobranza páginas reales de15, última y búsqueda después de50 a ${width}px`, async ({ browser, baseURL }, testInfo) => {
    const { context, page, state, errors } = await openOperationalPage(browser, baseURL, width, '/cobranza');
    try {
      await expect(page.locator('.cobranza-row')).toHaveCount(15);
      await expect(page.getByRole('button', { name: 'Todos 67', exact: true })).toBeVisible();
      await expect(page.getByText('67 documentos en seguimiento activo.', { exact: true })).toBeVisible();
      await expect(page.locator('.stat').filter({ hasText: 'Saldo total pendiente' }).locator('.stat-value')).toHaveText('S/ 6,700.00');
      const pagination = page.getByRole('navigation', { name: 'Paginación de cobranza' });
      await pagination.getByRole('button', { name: 'Ir a página 5', exact: true }).click();
      await expect(page.locator('.cobranza-row')).toHaveCount(7);
      await expect(page.getByText('Mostrando 61–67 de 67 documentos', { exact: true })).toBeVisible();
      await expect(pagination.getByRole('button', { name: 'Página siguiente' })).toBeDisabled();
      await expect(page.locator('.cobranza-total-footer')).toContainText('Saldo de esta página (7 documentos): S/ 700.00');
      expect(state.calls.some((call) => call.endpoint === '/cobranza/vencidas/page' && call.params.skip === '60' && call.params.limit === '15')).toBe(true);
      await assertViewportAndCapture(page, testInfo, `cobranza-last-${width}`);
      await page.getByPlaceholder('Buscar por cliente o numero de documento...').fill('Histórico');
      await expect(page.locator('.cobranza-row')).toHaveCount(1);
      await expect(page.locator('.cobranza-row')).toContainText('Comercial Histórico');
      await expect(page.getByText('Mostrando 1–1 de 1 documentos', { exact: true })).toBeVisible();
      expect(state.calls.filter((call) => call.endpoint === '/cobranza/vencidas/page').at(-1).params.skip).toBe('0');
      await page.getByPlaceholder('Buscar por cliente o numero de documento...').fill('');
      await expect(page.getByRole('button', { name: 'Críticos 17', exact: true })).toBeVisible();
      await page.getByRole('button', { name: 'Críticos 17', exact: true }).click();
      await expect(page.getByText('Mostrando 1–15 de 17 documentos', { exact: true })).toBeVisible();
      await pagination.getByRole('button', { name: 'Página siguiente' }).click();
      await expect(page.locator('.cobranza-row')).toHaveCount(2);
      await expect(page.getByText('Mostrando 16–17 de 17 documentos', { exact: true })).toBeVisible();
      expect(state.mutations).toEqual([]);
      expect(state.unexpected).toEqual([]);
      errors.assertClean();
    } finally { await context.close(); }
  });

  test(`devoluciones antiguas y paginación independiente a ${width}px`, async ({ browser, baseURL }, testInfo) => {
    const { context, page, state, errors } = await openOperationalPage(browser, baseURL, width, '/inventario?tab=returns');
    try {
      await expect(page.locator('.inventory-return-card')).toHaveCount(15);
      await expect(page.getByRole('tab', { name: 'Devoluciones 37', exact: true })).toBeVisible();
      const pagination = page.getByRole('navigation', { name: 'Paginación de devoluciones' });
      await pagination.getByRole('button', { name: 'Ir a página 3', exact: true }).click();
      await expect(page.locator('.inventory-return-card')).toHaveCount(7);
      await expect(page.getByRole('heading', { name: 'NC-037', exact: true })).toBeVisible();
      await expect(page.getByText('Mostrando 31–37 de 37 devoluciones', { exact: true })).toBeVisible();
      expect(state.calls.some((call) => call.endpoint === '/inventario/devoluciones/page' && call.params.skip === '30' && call.params.limit === '15')).toBe(true);
      await assertViewportAndCapture(page, testInfo, `returns-last-${width}`);
      await page.getByRole('tab', { name: 'Kardex 0', exact: true }).click();
      await page.getByRole('tab', { name: 'Devoluciones 37', exact: true }).click();
      await expect(pagination.getByRole('button', { name: 'Ir a página 3' })).toHaveAttribute('aria-current', 'page');
      state.returns = state.returns.slice(0, 30);
      await page.getByRole('button', { name: 'Actualizar', exact: true }).click();
      await expect(page.locator('.inventory-return-card')).toHaveCount(15);
      await expect(page.getByRole('heading', { name: 'NC-030', exact: true })).toBeVisible();
      await expect(page.getByText('Mostrando 16–30 de 30 devoluciones', { exact: true })).toBeVisible();
      expect(state.calls.filter((call) => call.endpoint === '/inventario/kardex/page').every((call) => call.params.skip === '0')).toBe(true);
      expect(state.mutations).toEqual([]);
      expect(state.unexpected).toEqual([]);
      errors.assertClean();
    } finally { await context.close(); }
  });
}

test('cobranza ajusta última página al saldar y descarta respuestas antiguas', async ({ browser, baseURL }) => {
  const { context, page, state, errors } = await openOperationalPage(browser, baseURL, 1440, '/cobranza', { debtCount: 31 });
  try {
    const pagination = page.getByRole('navigation', { name: 'Paginación de cobranza' });
    await expect(page.locator('.cobranza-row')).toHaveCount(15);
    await pagination.getByRole('button', { name: 'Ir a página 3', exact: true }).click();
    await expect(page.locator('.cobranza-row')).toHaveCount(1);
    await page.getByRole('button', { name: 'Saldar F001-000031 por S/ 100.00', exact: true }).click();
    await page.getByRole('dialog', { name: 'Saldar cuenta' }).getByRole('button', { name: 'Confirmar S/ 100.00', exact: true }).click();
    await expect(page.getByText('Mostrando 16–30 de 30 documentos', { exact: true })).toBeVisible();
    await expect(pagination.getByRole('button', { name: 'Ir a página 2', exact: true })).toHaveAttribute('aria-current', 'page');
    let release;
    let started;
    const searchStarted = new Promise((resolve) => { started = resolve; });
    state.heldSearch = { query: 'cliente 001', started, wait: new Promise((resolve) => { release = resolve; }) };
    const search = page.getByPlaceholder('Buscar por cliente o numero de documento...');
    await search.fill('Cliente 001');
    await searchStarted;
    await search.fill('Cliente 002');
    await expect(page.locator('.cobranza-row')).toHaveCount(1);
    await expect(page.locator('.cobranza-row')).toContainText('Cliente 002');
    const staleResponse = page.waitForResponse((response) => new URL(response.url()).searchParams.get('q') === 'Cliente 001');
    release();
    await staleResponse;
    await expect(page.locator('.cobranza-row')).toContainText('Cliente 002');
    expect(state.mutations).toEqual(['/cotizaciones/31/pagos']);
    expect(state.unexpected).toEqual([]);
    errors.assertClean();
  } finally { await context.close(); }
});
