import { expect, test } from '@playwright/test';
import { TENANT_STORAGE_STATE } from './helpers/auth';

async function openDashboardMockup(browser, baseURL, viewport) {
  const context = await browser.newContext({
    baseURL,
    viewport,
    storageState: process.env.E2E_TENANT_EMAIL
      ? TENANT_STORAGE_STATE
      : { cookies: [], origins: [] },
    reducedMotion: 'no-preference',
  });
  const page = await context.newPage();
  await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
  await expect(page.getByTestId('dashboard-business-mockup')).toBeVisible();
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
        await expect(page.getByText('S/ 10,000')).toBeVisible();
        await expect(page.getByText('S/ 2,750')).toBeVisible();
        if (viewport.width === 1024) {
          const visibleChartHeight = await page.locator('.business-sales').evaluate((element) => {
            const rect = element.getBoundingClientRect();
            return Math.max(0, Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0));
          });
          expect(visibleChartHeight).toBeGreaterThan(150);
        }
        if (viewport.width === 390 && process.env.MOCKUP_MOBILE_SCREENSHOT_PATH) {
          await page.screenshot({ path: process.env.MOCKUP_MOBILE_SCREENSHOT_PATH });
        }
        if (viewport.width === 390) {
          await page.getByRole('button', { name: 'Papel bond A4', exact: true }).click();
          await expect(page.getByRole('dialog', { name: 'Papel bond A4' })).toBeVisible();
          const dialogOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
          expect(dialogOverflow).toBe(false);
          await page.getByRole('button', { name: 'Cerrar detalle' }).click();
        }
        if (viewport.width === 1440 && process.env.MOCKUP_SCREENSHOT_PATH) {
          await page.screenshot({ path: process.env.MOCKUP_SCREENSHOT_PATH });
        }
      } finally {
        await context.close();
      }
    });
  }

  test('permite comparar cotizaciones y cambiar el seguimiento sin recargar', async ({ browser, baseURL }) => {
    const { context, page } = await openDashboardMockup(browser, baseURL, { width: 1280, height: 900 });
    try {
      const firstMetric = page.locator('.business-metric').first();
      const metricAnimation = await firstMetric.evaluate((element) => getComputedStyle(element).animationName);
      expect(metricAnimation).toContain('business-metric-arrive');
      await firstMetric.hover();
      await page.waitForTimeout(260);
      const hoverTransform = await firstMetric.evaluate((element) => getComputedStyle(element).transform);
      expect(hoverTransform).not.toBe('none');

      const quoted = page.getByRole('checkbox', { name: 'Mostrar importe cotizado' });
      await expect(quoted).toBeChecked();
      await quoted.uncheck();
      await expect(quoted).not.toBeChecked();
      await quoted.check();
      await expect(quoted).toBeChecked();

      const augustPoint = page.getByRole('button', { name: /Agosto: ventas S\/ 16,300/ });
      const augustHitArea = await augustPoint.evaluate((element) => element.getBoundingClientRect().height);
      expect(augustHitArea).toBeGreaterThan(200);
      await augustPoint.hover();
      await expect(page.getByRole('tooltip')).toContainText('Ventas registradas');
      await expect(page.getByRole('tooltip')).toContainText('S/ 16,300');
      await expect(page.getByRole('tooltip')).toContainText('Importe cotizado');
      await expect(page.getByRole('tooltip')).toContainText('S/ 14,500');
      if (process.env.MOCKUP_TOOLTIP_SCREENSHOT_PATH) {
        await page.screenshot({ path: process.env.MOCKUP_TOOLTIP_SCREENSHOT_PATH });
      }
      await augustPoint.focus();
      await expect(page.getByRole('tooltip')).toBeVisible();

      const septemberPoint = page.getByRole('button', { name: /Septiembre: ventas S\/ 9,800/ });
      await septemberPoint.hover();
      await expect(page.getByRole('tooltip')).toContainText('Mismo tramo de agosto');
      await septemberPoint.click();
      await expect(page.getByRole('dialog', { name: 'Ventas de Septiembre' })).toBeVisible();
      await expect(page.getByRole('dialog')).toContainText('1–26 sep 2026');
      await page.getByRole('button', { name: 'Cerrar detalle' }).click();

      const selectedCount = page.getByRole('tab', { name: /Cotizaciones sin una venta/ }).locator('span');
      await expect(selectedCount).toHaveText('12');
      const selectedCounterColors = await selectedCount.evaluate((element) => {
        const style = getComputedStyle(element);
        return { color: style.color, background: style.backgroundColor };
      });
      expect(selectedCounterColors.color).not.toBe(selectedCounterColors.background);

      await page.getByLabel('Ordenar productos').selectOption('decline');
      const firstProduct = page.locator('.business-ranking').first().locator('.business-ranking__entity').first();
      await expect(firstProduct).toHaveText('Papel bond A3');
      await firstProduct.click();
      await expect(page.getByRole('dialog', { name: 'Papel bond A3' })).toBeVisible();
      await expect(page.getByRole('dialog')).toContainText('S/ 2,600');
      await page.getByRole('button', { name: 'Cerrar detalle' }).click();

      const inactive = page.getByRole('tab', { name: /Sin compras en 60 días/ });
      await inactive.click();
      await expect(inactive).toHaveAttribute('aria-selected', 'true');
      await expect(page.getByText('Servicios Delta')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Ver todos los clientes' })).toBeVisible();
    } finally {
      await context.close();
    }
  });
});
