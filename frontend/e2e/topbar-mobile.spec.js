import { test, expect } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const apiOrigin = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const routes = [['/facturas', 'Facturas'], ['/clientes', 'Clientes'], ['/comprobantes/nuevo', 'Crear comprobante']];

for (const theme of ['light', 'dark']) {
  test(`encabezado móvil ${theme}: título y controles permanecen en una fila`, async ({ browser, baseURL }, testInfo) => {
    const context = await browser.newContext({ baseURL, viewport: { width: 320, height: 850 }, storageState: { cookies: [], origins: [] } });
    await context.addInitScript((value) => {
      localStorage.setItem('token', 'offline-topbar-qa');
      localStorage.setItem('inkora-theme', value);
    }, theme);
    const page = await context.newPage();
    const errors = attachCriticalErrorCollector(page);
    const unexpected = [];
    const payloads = {
      '/users/me': { id: 9, tenant_id: 74, rol: 'admin', is_active: true, is_superadmin: false, nombre_completo: 'Encabezado QA', email: 'qa@inkora.test', must_change_password: false },
      '/tenant': { id: 74, business_name: 'Encabezado QA', business_ruc: '20999999999', is_active: true, inventory_enabled: false },
      '/tenant/subscription-status': { fiscal_feature_flags: {} },
      '/sunat/exchange-rate': { buy: 3.7, sell: 3.72 },
      '/clientes/page': { items: [], total: 0, counts: { all: 0, empresa: 0, persona: 0, credito: 0, incompletos: 0 } },
      '/facturas-emitidas/page': { items: [], total: 0, counts: { all: 0 } },
      '/productos/page': { items: [], total: 0 },
      '/inventario/almacenes': [],
    };
    await page.route('**/*', async (route) => {
      const request = route.request(), url = new URL(request.url());
      if (!['fetch', 'xhr'].includes(request.resourceType())) {
        if (url.origin === new URL(baseURL).origin || ['data:', 'blob:'].includes(url.protocol)) await route.continue();
        else { unexpected.push(request.url()); await route.abort(); }
        return;
      }
      const path = url.pathname.replace(/\/$/, '');
      if (url.origin !== apiOrigin || request.method() !== 'GET' || !(path in payloads)) {
        unexpected.push(`${request.method()} ${path}`); await route.abort(); return;
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payloads[path]) });
    });
    try {
      for (const width of [320, 360, 380, 390, 428]) {
        await page.setViewportSize({ width, height: 850 });
        for (const [path, titleText] of routes) {
          await page.goto(path);
          const title = page.locator('.app-topbar__title').getByRole('heading', { name: titleText, exact: true });
          const menu = page.getByRole('button', { name: 'Abrir menú', exact: true });
          const notifications = page.getByRole('button', { name: 'Ver notificaciones', exact: true });
          await expect(title).toBeVisible();
          await expect(menu).toBeVisible();
          const [heading, toggle, actions, header] = await Promise.all([
            title.boundingBox(), menu.boundingBox(), notifications.boundingBox(), page.locator('.app-topbar').boundingBox(),
          ]);
          await page.screenshot({ path: testInfo.outputPath(`${path.split('/')[1]}-${width}.png`), animations: 'disabled' });
          expect(Math.abs(heading.y + heading.height / 2 - actions.y - actions.height / 2)).toBeLessThan(2);
          expect(Math.abs(heading.y + heading.height / 2 - toggle.y - toggle.height / 2)).toBeLessThan(6);
          expect(heading.x).toBeGreaterThanOrEqual(toggle.x + toggle.width + 3);
          expect(heading.x + heading.width).toBeLessThanOrEqual(actions.x - 3);
          expect(header.height).toBeLessThanOrEqual(80);
          for (const name of ['Ver notificaciones', 'Abrir menú de usuario', 'Crear comprobante']) {
            const button = page.locator('.app-topbar').getByRole('button', { name, exact: true }).filter({ visible: true });
            await expect(button).toBeVisible();
            const bounds = await button.boundingBox();
            expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
          }
          if (titleText !== 'Crear comprobante') {
            expect(await title.evaluate((node) => node.scrollWidth <= node.clientWidth + 1)).toBe(true);
          }
          await menu.click();
          await page.getByRole('button', { name: 'Cerrar menú', exact: true }).click();
          await expect(menu).toBeVisible();
        }
      }
      expect(unexpected).toEqual([]);
      errors.assertClean();
    } finally { await context.close(); }
  });
}
