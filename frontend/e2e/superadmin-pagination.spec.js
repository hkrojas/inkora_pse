import { test, expect } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const tenant = {
  id: 7, business_name: 'Pagination Tenant', business_ruc: '20606751509', business_address: 'Lima',
  plan_type: 'founder', is_active: true, has_smartpse_credentials: true, smartpse_status: 'ok',
  smartpse_company_id: 'company-7', smartpse_environment: 'demo', smartpse_remote_active: true,
  has_smartpse_gre_credentials: true, smartpse_gre_status: 'ok',
};
const members = Array.from({ length: 37 }, (_, index) => ({
  id: index + 1, email: `member${String(index + 1).padStart(2, '0')}@pagination.test`,
  nombre_completo: `Member ${index + 1}`, rol: 'vendedor', is_active: true,
  metrics: Object.fromEntries(['cotizaciones_total', 'cotizaciones_mes_actual', 'facturas_total', 'facturas_mes_actual',
    'boletas_total', 'boletas_mes_actual', 'notas_credito_total', 'guias_total', 'guias_mes_actual'].map((key) => [key, 0])),
}));
const companies = Array.from({ length: 37 }, (_, index) => ({
  id: `remote-${index + 1}`, ruc: `20${String(index + 1).padStart(9, '0')}`,
  razon_social: `Remote company ${String(index + 1).padStart(2, '0')}`, environment: 'demo', active: true,
}));
const incidents = Array.from({ length: 37 }, (_, index) => ({
  job_id: index + 1, action: 'emit_fiscal_document', resource_type: 'cotizacion', resource_id: index + 1,
  attempts: 2, last_error: `Fiscal incident ${String(index + 1).padStart(2, '0')}`, created_at: '2026-09-30T12:00:00Z',
}));
const audit = Array.from({ length: 37 }, (_, index) => ({
  id: index + 1, action: `superadmin.tenant.smartpse.checked-${String(index + 1).padStart(2, '0')}`,
  timestamp: '2026-09-30T12:00:00Z', entity_type: 'tenant', entity_id: tenant.id,
}));

async function setup(browser, baseURL, width) {
  const context = await browser.newContext({ baseURL, viewport: { width, height: 900 },
    reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
  await context.addInitScript(() => { localStorage.setItem('token', 'local-pagination-fixture'); });
  const page = await context.newPage();
  const calls = [];
  const writes = [];
  const errors = attachCriticalErrorCollector(page);
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    calls.push(url);
    if (request.method() !== 'GET') writes.push(`${request.method()} ${path}`);
    let payload = {};
    if (path === '/users/me') payload = { id: 700, email: 'pagination-root@inkora.test', rol: 'superadmin',
      nombre_completo: 'Pagination QA', is_superadmin: true, must_change_password: false, tenant_id: null };
    else if (path === '/tenant') payload = tenant;
    else if (path === '/sunat/exchange-rate') payload = { buy: '3.5', sell: '3.6' };
    else if (path === '/superadmin/access-requests') payload = { items: [], total: 0, skip: 0, limit: 15 };
    else if (path === '/superadmin/tenants-page') payload = { items: [tenant], total: 1, skip: 0, limit: 15,
      metrics: { total: 1, active: 1, smartpse_gre: 1, smartpse_gre_pending: 0 } };
    else if (path === '/superadmin/smartpse/companies') {
      const selected = companies.filter((row) => row.razon_social.toLowerCase().includes((url.searchParams.get('search') || '').toLowerCase()));
      const number = Number(url.searchParams.get('page')) || 1;
      const size = Number(url.searchParams.get('per_page')) || 15;
      payload = { data: selected.slice((number - 1) * size, number * size), total: selected.length,
        current_page: number, last_page: Math.max(1, Math.ceil(selected.length / size)) };
    } else if (path.endsWith('/users-detail')) payload = members;
    else if (path.endsWith('/smartpse/company')) payload = { id: 'company-7', ruc: tenant.business_ruc, razon_social: tenant.business_name };
    else if (path.endsWith('/emission-errors/page') || path.endsWith('/smartpse/audit-logs/page')) {
      const rows = path.endsWith('/emission-errors/page') ? incidents : audit;
      const skip = Number(url.searchParams.get('skip')) || 0;
      const limit = Number(url.searchParams.get('limit')) || 15;
      payload = { items: rows.slice(skip, skip + limit), total: rows.length, skip, limit };
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
  });
  await page.goto('/superadmin');
  await expect(page.getByRole('heading', { name: 'Panel de empresas', exact: true })).toBeVisible();
  return { context, page, calls, writes, errors };
}

async function lastPage(page, label) {
  const pager = page.getByRole('navigation', { name: label, exact: true });
  await expect(pager.getByRole('button', { name: 'Ir a página 3', exact: true })).toBeVisible();
  await pager.getByRole('button', { name: 'Ir a página 2', exact: true }).click();
  return pager;
}

async function assertMobilePager(page, pager) {
  await pager.scrollIntoViewIfNeeded();
  const bounds = await pager.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(page.viewportSize().width + 1);
  expect(await pager.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
}

// StrictMode may repeat the initial effect; the pagination sequence must still advance once per choice.
function distinctConsecutive(values) {
  return values.filter((value, index) => index === 0 || value !== values[index - 1]);
}

async function openTenantMenu(page) {
  const label = `Más opciones para ${tenant.business_name}`;
  await page.getByRole('button', { name: label, exact: true }).click();
  const menu = page.getByRole('group', { name: label, exact: true });
  await expect(menu).toBeVisible();
  await assertMobilePager(page, menu);
  return menu;
}

for (const width of [1440, 390]) {
  test(`Superadmin: empresas remotas paginan 15/15/7 y búsqueda reinicia a ${width}px`, async ({ browser, baseURL }) => {
    const { context, page, calls, writes, errors } = await setup(browser, baseURL, width);
    try {
      const cards = page.locator('.smartpse-company-card');
      await expect(cards).toHaveCount(15);
      await expect(page.getByText('Remote company 01', { exact: true })).toBeVisible();
      let pager = await lastPage(page, 'Paginación de empresas Smart PSE');
      await expect(page.getByText('Remote company 16', { exact: true })).toBeVisible();
      await expect(cards).toHaveCount(15);
      pager = page.getByRole('navigation', { name: 'Paginación de empresas Smart PSE', exact: true });
      await pager.getByRole('button', { name: 'Ir a página 3', exact: true }).click();
      await expect(cards).toHaveCount(7);
      await expect(page.getByText('Remote company 37', { exact: true })).toBeVisible();
      pager = page.getByRole('navigation', { name: 'Paginación de empresas Smart PSE', exact: true });
      await expect(pager.getByRole('button', { name: 'Página siguiente', exact: true })).toBeDisabled();
      await assertMobilePager(page, pager);
      const requests = calls.filter((url) => url.pathname === '/superadmin/smartpse/companies');
      expect(distinctConsecutive(requests.map((url) => Number(url.searchParams.get('page'))))).toEqual([1, 2, 3]);
      expect(requests.every((url) => url.searchParams.get('per_page') === '15')).toBe(true);
      await page.getByPlaceholder('Buscar por RUC o razón social…').fill('company 37');
      await expect(cards).toHaveCount(1);
      expect(calls.filter((url) => url.pathname === '/superadmin/smartpse/companies').at(-1).searchParams.get('page')).toBe('1');
      expect(writes).toEqual([]);
      errors.assertClean();
    } finally { await context.close(); }
  });

  test(`Superadmin: usuarios e incidencias conservan sus 37 resultados a ${width}px`, async ({ browser, baseURL }) => {
    const { context, page, calls, writes, errors } = await setup(browser, baseURL, width);
    try {
      const usersMenu = await openTenantMenu(page);
      await usersMenu.getByRole('button', { name: 'Usuarios', exact: true }).click();
      const dialog = page.getByRole('dialog');
      await expect(dialog.getByText(/^member\d{2}@pagination.test$/)).toHaveCount(15);
      const initialUsersRequests = calls.filter((url) => url.pathname.endsWith('/users-detail')).length;
      expect(initialUsersRequests).toBeGreaterThan(0);
      await lastPage(page, 'Paginación de usuarios de la empresa');
      await expect(dialog.getByText('member16@pagination.test', { exact: true })).toBeVisible();
      await expect(dialog.getByText(/^member\d{2}@pagination.test$/)).toHaveCount(15);
      let pager = page.getByRole('navigation', { name: 'Paginación de usuarios de la empresa', exact: true });
      await pager.getByRole('button', { name: 'Ir a página 3', exact: true }).click();
      await expect(dialog.getByText(/^member\d{2}@pagination.test$/)).toHaveCount(7);
      await expect(dialog.getByText('member37@pagination.test', { exact: true })).toBeVisible();
      await assertMobilePager(page, pager);
      expect(calls.filter((url) => url.pathname.endsWith('/users-detail'))).toHaveLength(initialUsersRequests);
      await page.keyboard.press('Escape');
      const incidentsMenu = await openTenantMenu(page);
      await incidentsMenu.getByRole('button', { name: 'Incidencias fiscales', exact: true }).click();
      await expect(dialog.getByText(/^Fiscal incident \d{2}$/)).toHaveCount(15);
      await lastPage(page, 'Paginación de incidencias fiscales');
      await expect(dialog.getByText('Fiscal incident 16', { exact: true })).toBeVisible();
      pager = page.getByRole('navigation', { name: 'Paginación de incidencias fiscales', exact: true });
      await pager.getByRole('button', { name: 'Ir a página 3', exact: true }).click();
      await expect(dialog.getByText(/^Fiscal incident \d{2}$/)).toHaveCount(7);
      await expect(dialog.getByText('Fiscal incident 37', { exact: true })).toBeVisible();
      pager = page.getByRole('navigation', { name: 'Paginación de incidencias fiscales', exact: true });
      await expect(pager.getByRole('button', { name: 'Página siguiente', exact: true })).toBeDisabled();
      await assertMobilePager(page, pager);
      const requests = calls.filter((url) => url.pathname.endsWith('/emission-errors/page'));
      expect(distinctConsecutive(requests.map((url) => Number(url.searchParams.get('skip'))))).toEqual([0, 15, 30]);
      expect(requests.every((url) => url.searchParams.get('limit') === '15')).toBe(true);
      expect(writes).toEqual([]);
      errors.assertClean();
    } finally { await context.close(); }
  });

  test(`Superadmin: historial local Smart PSE conserva total y todas las páginas a ${width}px`, async ({ browser, baseURL }) => {
    const { context, page, calls, writes, errors } = await setup(browser, baseURL, width);
    try {
      await page.getByRole('button', { name: 'Editar empresa', exact: true }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByRole('button', { name: 'Ver historial', exact: true }).click();
      const rows = dialog.getByText(/^superadmin\.tenant\.smartpse\.checked-\d{2}$/);
      await expect(rows).toHaveCount(15);
      await expect(dialog.getByText('37 acciones registradas en Inkora para esta empresa.', { exact: true })).toBeVisible();
      await lastPage(page, 'Paginación del historial Smart PSE');
      await expect(dialog.getByText('superadmin.tenant.smartpse.checked-16', { exact: true })).toBeVisible();
      const pager = page.getByRole('navigation', { name: 'Paginación del historial Smart PSE', exact: true });
      await pager.getByRole('button', { name: 'Ir a página 3', exact: true }).click();
      await expect(rows).toHaveCount(7);
      await expect(dialog.getByText('superadmin.tenant.smartpse.checked-37', { exact: true })).toBeVisible();
      await assertMobilePager(page, pager);
      const requests = calls.filter((url) => url.pathname.endsWith('/smartpse/audit-logs/page'));
      expect(distinctConsecutive(requests.map((url) => Number(url.searchParams.get('skip'))))).toEqual([0, 15, 30]);
      expect(requests.every((url) => url.searchParams.get('limit') === '15')).toBe(true);
      expect(writes).toEqual([]);
      errors.assertClean();
    } finally { await context.close(); }
  });
}
