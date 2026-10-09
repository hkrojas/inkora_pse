import { expect, test } from '@playwright/test';

test.setTimeout(60000);
for (const entry of ['actions', 'bajas']) {
  for (const theme of ['light', 'dark']) {
    for (const width of [320, 390, 1440]) {
      test(`baja ${entry} ${theme} ${width}: confirmación explícita y seguimiento sin reenviar`, async ({ page }, testInfo) => {
        await page.setViewportSize({ width, height: 900 });
        await page.clock.install();
        await page.goto(`/e2e/void-recovery.html?entry=${entry}&theme=${theme}`);
        if (entry === 'actions') {
          await page.getByRole('button', { name: 'Más acciones de B001-000042' }).click();
          await page.getByRole('button', { name: 'Dar de baja', exact: true }).click();
          await page.getByLabel('Motivo de baja', { exact: true }).fill('Documento no entregado');
        } else {
          await page.clock.runFor(400);
          await page.getByRole('button', { name: 'Baja', exact: true }).click();
          await page.getByRole('button', { name: 'Confirmar baja', exact: true }).click();
        }
        const dialog = page.getByRole('dialog', { name: entry === 'actions' ? 'Solicitar baja' : 'Confirmar comunicación de baja', exact: true });
        const submit = dialog.getByRole('button', { name: entry === 'actions' ? 'Confirmar' : 'Confirmar baja', exact: true });
        await expect(submit).toBeDisabled();
        await expect(page.getByText(/Confirmo que el comprobante no fue entregado/)).toBeVisible();
        if (width === 390) {
          await page.clock.runFor(400);
          await page.screenshot({ path: testInfo.outputPath('confirmacion.png'), fullPage: true });
        }
        await dialog.getByRole('checkbox').check();
        await expect(submit).toBeEnabled();
        await submit.click();
        await expect.poll(() => page.evaluate(() => window.voidQa.calls.filter((call) => call.path === '/bajas/anular').length)).toBe(1);
        const posted = await page.evaluate(() => window.voidQa.calls.find((call) => call.path === '/bajas/anular').payload);
        expect(posted.confirmed_not_delivered).toBe(true);
        expect(posted.comprobante_id).toBe(42);
        await page.evaluate(() => { window.voidQa.status = 'retry'; window.voidQa.revision += 1; });
        await page.clock.runFor(6000);
        await expect.poll(() => page.evaluate(() => window.voidQa.calls.filter((call) => call.path === '/emission-jobs/7001').length)).toBeGreaterThan(0);
        await page.evaluate(() => { window.voidQa.status = 'succeeded'; window.voidQa.revision += 1; });
        await page.clock.runFor(31000);
        await expect(page.getByText('Baja aceptada por SUNAT', { exact: entry === 'actions' })).toBeVisible();
        expect(await page.evaluate(() => window.voidQa.calls.filter((call) => call.path === '/bajas/anular').length)).toBe(1);
        const geometry = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
        expect(geometry.scroll).toBeLessThanOrEqual(geometry.width + 1);
        if (width === 390) await page.screenshot({ path: testInfo.outputPath('aceptada.png'), fullPage: true });
      });
    }
  }
}
