import { expect, test } from '@playwright/test';
import { recordsPayload } from './helpers/dashboard-records';
import { chooseInkoraOption } from './helpers/inkora-controls';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;

const visualPayload = {
  meta: {
    generated_at: '2026-09-28T12:30:00-05:00',
    currency: 'PEN',
    period: { start: '2026-09-01', end: '2026-09-28', label: '1–28 sep 2026' },
    comparison: { start: '2026-08-01', end: '2026-08-28', label: '1–28 ago 2026' },
    history: { start: '2026-07-12', end: '2026-09-28', label: '12 jul – 28 sep 2026' },
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
    { year: 2026, month: 7, sales_amount: '7100.00', quoted_amount: '8500.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 8, sales_amount: '10004.00', quoted_amount: '11500.00', is_partial: false, cutoff_day: null, previous_matched_sales: null },
    { year: 2026, month: 9, sales_amount: '12345.00', quoted_amount: '14000.00', is_partial: true, cutoff_day: 28, previous_matched_sales: '10004.00' },
  ],
  conversion: { available: true, reason: null, quote_count: 5, linked_sales_count: 2, rate_percent: '40.0' },
  products: [
    { id: 911, name: 'Resma API Única', unit: 'NIU', quantity: '7.00', amount: '7777.00', previous_amount: '7000.00', change_percent: '11.1' },
    { id: 912, name: 'Tinta API Azul', unit: 'NIU', quantity: '4.00', amount: '4568.00', previous_amount: '5000.00', change_percent: '-8.6' },
  ],
  clients: [
    { id: 731, name: 'Cliente API Único', amount: '8000.00', purchases: 2, last_purchase: '2026-09-25', share_percent: '64.8', previous_amount: '7000.00', change_percent: '14.3' },
    { id: 732, name: 'Cliente API Dos', amount: '4345.00', purchases: 1, last_purchase: '2026-09-20', share_percent: '35.2', previous_amount: '3004.00', change_percent: '44.6' },
  ],
  follow_up: {
    quotes: { available: true, reason: null, count: 3, rows: [{ quote_id: 300, client_id: 733, client: 'Cliente por cotización', reference: 'COT-000300', amount: '800.00', age_days: 6 }] },
    declining: { available: true, reason: null, count: 1, rows: [{ client_id: 732, client: 'Cliente API Dos', reference: 'Ventas del periodo', amount: '4345.00', age_days: 8 }] },
    inactive: { available: true, reason: null, count: 1, rows: [{ client_id: 733, client: 'Cliente API Inactivo', reference: 'Última compra', amount: '900.00', age_days: 68 }] },
  },
  pending: { low_stock_products: 6, fiscal_documents_with_errors: 2 },
};

async function openDashboardMockup(browser, baseURL, viewport) {
  const context = await browser.newContext({
    baseURL,
    viewport,
    hasTouch: viewport.width < 600,
    isMobile: viewport.width < 600,
    storageState: { cookies: [], origins: [] },
    reducedMotion: 'no-preference',
  });
  await context.addInitScript(() => localStorage.setItem('token', 'dashboard-visual-e2e-token'));
  const page = await context.newPage();
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    let body = {};
    if (path === '/users/me') {
      body = {
        id: 7301,
        email: 'dashboard.visual@inkora.test',
        nombre_completo: 'Operador Dashboard',
        rol: 'admin',
        is_superadmin: false,
        must_change_password: false,
        tenant_id: 73,
      };
    } else if (path === '/analytics/dashboard/business') {
      body = visualPayload;
    } else if (path === '/analytics/dashboard/business/records') {
      body = recordsPayload(url.searchParams);
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
  await expect(page.getByTestId('dashboard-business-mockup')).toBeVisible();
  await expect(page.getByText('Resma API Única')).toBeVisible();
  await page.waitForTimeout(1100);
  return { context, page };
}

test.describe('Mockup comercial del dashboard', () => {
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 1024, height: 768 },
    { width: 390, height: 844 },
  ]) {
    test(`mantiene el contenido dentro de la pantalla a ${viewport.width}px`, async ({ browser, baseURL }) => {
      const { context, page } = await openDashboardMockup(browser, baseURL, viewport);
      try {
        const overflow = await page.locator('main').evaluate((element) => element.scrollWidth > element.clientWidth + 1);
        expect(overflow).toBe(false);
        const chartLayout = await page.locator('.business-chart__viewport').evaluate((element) => {
          const viewport = element.getBoundingClientRect();
          const svg = element.querySelector('svg').getBoundingClientRect();
          return {
            overflowX: getComputedStyle(element).overflowX,
            svgFits: svg.left >= viewport.left - 1 && svg.right <= viewport.right + 1,
          };
        });
        expect(chartLayout.overflowX).toBe('hidden');
        expect(chartLayout.svgFits).toBe(true);
        await expect(page.getByRole('heading', { name: 'Tu negocio, de un vistazo' })).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Resumen', level: 1 })).toBeVisible();
        await expect(page.locator('.business-metric__value').getByText('S/ 12,345', { exact: true })).toBeVisible();
        await expect(page.locator('.business-metric__value').getByText('S/ 987', { exact: true })).toBeVisible();
        if (viewport.width === 1024) {
          const visibleChartHeight = await page.locator('.business-sales').evaluate((element) => {
            const rect = element.getBoundingClientRect();
            return Math.max(0, Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0));
          });
          expect(visibleChartHeight).toBeGreaterThan(150);
        }
        if (viewport.width === 390 && process.env.MOCKUP_MOBILE_SCREENSHOT_PATH) {
          await page.locator('.business-sales').screenshot({ path: process.env.MOCKUP_MOBILE_SCREENSHOT_PATH });
        }
        if (viewport.width === 390) {
          await page.getByRole('button', { name: 'Resma API Única', exact: true }).click();
          await expect(page.getByRole('dialog', { name: 'Ventas de Resma API Única' })).toBeVisible();
          await expect(page).toHaveURL(/\/dashboard$/);
          await page.getByRole('button', { name: 'Cerrar detalle' }).click();
          await expect(page.getByText('Resma API Única')).toBeVisible();
        }
        if (viewport.width === 1440 && process.env.MOCKUP_SCREENSHOT_PATH) {
          await page.locator('.business-sales').screenshot({ path: process.env.MOCKUP_SCREENSHOT_PATH });
        }
      } finally {
        await context.close();
      }
    });
  }

  test('expone el historial real y abre drill-downs con filtros', async ({ browser, baseURL }) => {
    const { context, page } = await openDashboardMockup(browser, baseURL, { width: 1280, height: 900 });
    try {
      const firstMetric = page.locator('.business-metric').first();
      const metricAnimation = await firstMetric.evaluate((element) => getComputedStyle(element).animationName);
      expect(metricAnimation).toContain('business-metric-arrive');
      await firstMetric.hover();
      await page.waitForTimeout(260);
      const hoverTransform = await firstMetric.evaluate((element) => getComputedStyle(element).transform);
      expect(hoverTransform).not.toBe('none');

      const quoted = page.getByRole('checkbox');
      await expect(quoted).toBeEnabled();
      await expect(quoted).toBeChecked();
      await expect(page.getByText('2 de 5 cotizaciones', { exact: false })).toBeVisible();
      await quoted.uncheck();
      await expect(page.locator('.business-chart__line--quoted')).toHaveCount(0);
      await quoted.check();
      await expect(page.locator('.business-chart__line--quoted')).toHaveCount(1);

      const augustPoint = page.getByRole('button', { name: /Agosto 2026: ventas S\/ 10[,.]004/ });
      const augustHitArea = await augustPoint.evaluate((element) => element.getBoundingClientRect().height);
      expect(augustHitArea).toBeGreaterThan(200);
      await augustPoint.hover();
      await expect(page.getByRole('tooltip')).toContainText('Ventas registradas');
      await expect(page.getByRole('tooltip')).toContainText('S/ 10,004');
      if (process.env.MOCKUP_TOOLTIP_SCREENSHOT_PATH) {
        await page.screenshot({ path: process.env.MOCKUP_TOOLTIP_SCREENSHOT_PATH });
      }
      await augustPoint.focus();
      await expect(page.getByRole('tooltip')).toBeVisible();

      const septemberPoint = page.getByRole('button', { name: /Septiembre 2026: ventas S\/ 12[,.]345/ });
      await septemberPoint.hover();
      await expect(page.getByRole('tooltip')).toContainText('Mismo tramo anterior');
      await septemberPoint.click();
      await expect(page.getByRole('dialog', { name: 'Ventas de Septiembre 2026' })).toBeVisible();
      await expect(page).toHaveURL(/\/dashboard$/);
      await page.getByRole('button', { name: 'Cerrar detalle' }).click();
      await expect(page.getByText('Resma API Única')).toBeVisible();

      const selectedCount = page.getByRole('tab', { name: /Cotizaciones sin una venta/ }).locator('span');
      await expect(selectedCount).toHaveText('3');
      const selectedCounterColors = await selectedCount.evaluate((element) => {
        const style = getComputedStyle(element);
        return { color: style.color, background: style.backgroundColor };
      });
      expect(selectedCounterColors.color).not.toBe(selectedCounterColors.background);

      await chooseInkoraOption(page, 'Ordenar productos', 'Mayor caída');
      const firstProduct = page.locator('.business-ranking').first().locator('.business-ranking__entity').first();
      await expect(firstProduct).toHaveText('Tinta API Azul');
      await firstProduct.click();
      await expect(page.getByRole('dialog', { name: 'Ventas de Tinta API Azul' })).toBeVisible();
      await page.getByRole('button', { name: 'Cerrar detalle' }).click();
      await expect(page.getByText('Resma API Única')).toBeVisible();

      const inactive = page.getByRole('tab', { name: /Sin compras en 60 días/ });
      await inactive.click();
      await expect(inactive).toHaveAttribute('aria-selected', 'true');
      await expect(page.getByText('Cliente API Inactivo')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Ver todos los clientes' })).toBeVisible();
    } finally {
      await context.close();
    }
  });
  test('móvil: letras legibles, ampliación y toque sin abandonar el gráfico', async ({ browser, baseURL }) => {
    const { context, page } = await openDashboardMockup(browser, baseURL, { width: 390, height: 844 });
    try {
      const svg = page.locator('.business-chart__svg');
      const geometry = await svg.evaluate((el) => ({ scale: el.getScreenCTM().a, height: el.getBoundingClientRect().height }));
      expect(geometry.scale).toBeCloseTo(1, 1);
      expect(geometry.height).toBeGreaterThanOrEqual(320);
      await page.getByRole('button', { name: 'Ampliar gráfico' }).tap();
      await expect(page.getByRole('button', { name: 'Reducir gráfico' })).toHaveAttribute('aria-expanded', 'true');
      expect((await svg.boundingBox()).height).toBe(480);
      const expandedGeometry = await svg.evaluate((el) => ({ scale: el.getScreenCTM().a, width: el.getBoundingClientRect().width, viewBox: el.getAttribute('viewBox'), labels: [...el.querySelectorAll('.business-chart__axis-label')].map(label => ({text: label.textContent, x: label.getBBox().x})) }));
      expect(expandedGeometry.scale).toBeCloseTo(1, 1);
      expect(expandedGeometry.labels.every(label => label.x >= 0)).toBe(true);
      const september = page.getByRole('button', { name: /Septiembre 2026: ventas/ });
      await september.tap();
      await expect(page).toHaveURL(/\/dashboard$/);
      expect(await page.locator('.business-chart__viewport').evaluate(el => el.scrollLeft)).toBe(0);
      await expect(page.locator('.business-chart__selection')).toContainText('S/ 12,345');
      await expect(page.locator('.business-chart__selection')).toContainText('S/ 14,000');
      await expect(page.locator('.business-chart__selection')).toContainText('Mismo tramo anterior');
      await page.locator('.business-chart__selection').scrollIntoViewIfNeeded();
      await page.screenshot({ path: 'test-results/dashboard-mobile-expanded.png' });
      await page.getByRole('button', { name: 'Ver registros de septiembre' }).tap();
      await expect(page.getByRole('dialog', { name: 'Ventas de Septiembre 2026' })).toBeVisible();
      await expect(page).toHaveURL(/\/dashboard$/);
    } finally { await context.close(); }
  });

  test('abre la cotización concreta desde seguimiento', async ({ browser, baseURL }) => {
    const { context, page } = await openDashboardMockup(browser, baseURL, { width: 1280, height: 900 });
    try {
      await page.getByRole('button', { name: 'Ver cotización', exact: true }).click();
      await expect(page).toHaveURL(/\/cotizaciones\/300$/);
    } finally { await context.close(); }
  });

});
