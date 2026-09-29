import { expect, test } from '@playwright/test';

async function openDashboardMockup(browser, baseURL, viewport) {
  const context = await browser.newContext({
    baseURL,
    viewport,
    storageState: { cookies: [], origins: [] },
    reducedMotion: 'no-preference',
  });
  const page = await context.newPage();
  await page.goto('/dashboard');
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
        await expect(page.getByRole('heading', { name: 'Tu negocio, de un vistazo' })).toBeVisible();
        await expect(page.getByText('S/ 10,000')).toBeVisible();
        await expect(page.getByText('S/ 2,750')).toBeVisible();
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

      const augustPoint = page.getByRole('button', { name: /Agosto: ventas S\/ 16,300/ });
      await augustPoint.hover();
      await expect(page.getByRole('tooltip')).toContainText('Ventas registradas');
      await expect(page.getByRole('tooltip')).toContainText('S/ 16,300');
      await augustPoint.focus();
      await expect(page.getByRole('tooltip')).toBeVisible();

      const inactive = page.getByRole('tab', { name: /Sin compras en 60 días/ });
      await inactive.click();
      await expect(inactive).toHaveAttribute('aria-selected', 'true');
      await expect(page.getByText('Servicios Delta')).toBeVisible();
    } finally {
      await context.close();
    }
  });
});
