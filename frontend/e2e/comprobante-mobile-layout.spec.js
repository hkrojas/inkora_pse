import { test, expect } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const apiOrigin = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const warehouseName = 'Almacén de producción y distribución con nombre largo';
const payloads = {
  '/users/me': { id: 9, tenant_id: 74, rol: 'admin', is_active: true, is_superadmin: false, nombre_completo: 'Diseño QA', must_change_password: false },
  '/tenant': { id: 74, business_name: 'Diseño QA', business_ruc: '20999999999', is_active: true, inventory_enabled: true },
  '/tenant/subscription-status': { fiscal_feature_flags: {} },
  '/sunat/exchange-rate': { buy: 3.7, sell: 3.72 },
  '/clientes/page': { items: [], total: 0 },
  '/productos/page': { items: [], total: 0 },
  '/productos/search': [],
  '/clientes/search': [],
  '/inventario/almacenes': [
    { id: 11, name: warehouseName, is_default: true },
    { id: 27, name: 'Casa', is_default: false },
  ],
};

async function assertFits(page) {
  const bounds = await page.evaluate(() => {
    const nav = document.querySelector('.comprobante-nuevo-page .section-navigation');
    const items = nav.querySelector('.section-navigation__items');
    const main = document.querySelector('main');
    return {
      viewport: innerWidth, document: document.documentElement.scrollWidth,
      page: document.querySelector('.comprobante-nuevo-page').getBoundingClientRect().right,
      mainClient: main.clientWidth, mainScroll: main.scrollWidth,
      itemsClient: items.clientWidth, itemsScroll: items.scrollWidth,
      emissionClient: document.querySelector('#document-emission').clientWidth,
      emissionScroll: document.querySelector('#document-emission').scrollWidth,
      steps: [...items.children].map(button => {
        const box = button.getBoundingClientRect();
        return { left: box.left, right: box.right, height: box.height, client: button.clientWidth, scroll: button.scrollWidth };
      }),
    };
  });
  expect(bounds.document).toBeLessThanOrEqual(bounds.viewport + 1);
  expect(bounds.page).toBeLessThanOrEqual(bounds.viewport + 1);
  expect(bounds.mainScroll).toBeLessThanOrEqual(bounds.mainClient + 1);
  expect(bounds.itemsScroll, 'todos los pasos caben sin scroll lateral').toBeLessThanOrEqual(bounds.itemsClient + 1);
  expect(bounds.emissionScroll, 'el formulario cabe incluso con nombres largos').toBeLessThanOrEqual(bounds.emissionClient + 1);
  for (const step of bounds.steps) {
    expect(step.left).toBeGreaterThanOrEqual(0);
    expect(step.right).toBeLessThanOrEqual(bounds.viewport + 1);
    expect(step.scroll).toBeLessThanOrEqual(step.client + 1);
    if (bounds.viewport <= 960) expect(step.height).toBeGreaterThanOrEqual(44);
  }
}

for (const theme of ['light', 'dark']) {
  for (const tipo of ['01', '03']) {
    test(`nuevo comprobante ${tipo} ${theme}: progreso y almacén caben y funcionan`, async ({ browser, baseURL }, testInfo) => {
      test.setTimeout(120_000);
      const context = await browser.newContext({ baseURL, viewport: { width: 320, height: 900 }, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
      await context.addInitScript(value => {
        localStorage.setItem('token', 'offline-layout-qa');
        localStorage.setItem('inkora-theme', value);
      }, theme);
      const page = await context.newPage();
      const errors = attachCriticalErrorCollector(page), unexpected = [];
      await page.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (!['fetch', 'xhr'].includes(request.resourceType())) {
          if (url.origin === new URL(baseURL).origin || ['data:', 'blob:'].includes(url.protocol)) await route.continue();
          else { unexpected.push(request.url()); await route.abort(); }
          return;
        }
        const payload = payloads[url.pathname.replace(/\/$/, '')];
        if (url.origin !== apiOrigin || request.method() !== 'GET' || payload === undefined) {
          unexpected.push(`${request.method()} ${url.pathname}`); await route.abort(); return;
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
      });
      try {
        await page.goto(`/comprobantes/nuevo?tipo=${tipo}`);
        const nav = page.getByRole('navigation', { name: 'Progreso de emisión', exact: true });
        await expect(nav.getByRole('button')).toHaveCount(4);
        const warehouse = page.getByRole('button', { name: 'Almacén de salida', exact: true });
        for (const width of [320, 360, 390, 640, 768, 1024, 1440]) {
          await page.setViewportSize({ width, height: 900 });
          await assertFits(page);
          await nav.getByRole('button', { name: 'Líneas Pendiente', exact: true }).click();
          await expect(page.locator('#document-lines')).toBeFocused();
          await expect(nav.getByRole('button', { name: 'Líneas Pendiente', exact: true })).toHaveAttribute('aria-current', 'step');
          await nav.getByRole('button', { name: 'Documento Configurado', exact: true }).click();
          await expect(page.locator('#document-emission')).toBeFocused();
          await expect(warehouse).toHaveClass(/ink-select-trigger/);
          await warehouse.click();
          const list = page.getByRole('listbox', { name: 'Almacén de salida', exact: true });
          await expect(list).toBeVisible();
          const box = await list.boundingBox();
          expect(box.x).toBeGreaterThanOrEqual(0);
          expect(box.x + box.width).toBeLessThanOrEqual(width);
          await expect(list.getByRole('option', { name: warehouseName + ' · Principal', exact: true })).toBeVisible();
          await page.screenshot({ path: testInfo.outputPath(`almacen-${width}.png`), animations: 'disabled' });
          await list.getByRole('option', { name: 'Casa', exact: true }).click();
          await expect(warehouse).toHaveText('Casa');
          await page.mouse.move(0, 0);
          await warehouse.press('ArrowDown');
          await expect(list).toBeVisible();
          await expect(warehouse).toHaveAttribute('aria-activedescendant', /option-1$/);
          await page.keyboard.press('ArrowUp');
          await expect(warehouse).toHaveAttribute('aria-activedescendant', /option-0$/);
          await page.keyboard.press('Enter');
          await expect(warehouse).toHaveText(warehouseName + ' · Principal');
          await expect(warehouse).toBeFocused();
          await warehouse.click();
          await page.keyboard.press('Escape');
          await expect(list).toHaveCount(0);
          await expect(warehouse).toBeFocused();
          await assertFits(page);
          await nav.scrollIntoViewIfNeeded();
          await page.screenshot({ path: testInfo.outputPath(`progreso-${width}.png`), animations: 'disabled' });
        }
        await page.getByRole('textbox', { name: 'Razón social o nombre', exact: true }).fill('Cliente QA');
        await page.getByRole('textbox', { name: 'Producto o descripción', exact: true }).fill('Servicio QA');
        await page.getByPlaceholder('0.00', { exact: true }).click();
        await page.getByPlaceholder('0.00', { exact: true }).fill('118');
        await nav.getByRole('button', { name: 'Documento Configurado', exact: true }).click();
        await expect(page.locator('.ink-combobox-menu')).toHaveCount(0);
        await page.setViewportSize({ width: 320, height: 900 });
        await expect(nav.getByRole('button', { name: 'Cliente Listo', exact: true })).toBeVisible();
        await expect(nav.getByRole('button', { name: 'Líneas 1 lista', exact: true })).toBeVisible();
        await assertFits(page);
        expect(unexpected).toEqual([]);
        errors.assertClean();
      } finally { await context.close(); }
    });
  }
}
