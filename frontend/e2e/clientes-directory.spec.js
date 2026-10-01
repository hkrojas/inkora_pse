import { expect, test } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const counts = { all: 183, empresa: 155, persona: 28, credito: 0, incompletos: 183 };
const clients = [
  { id: 1, tipo_documento: '6', numero_documento: '20123456789', razon_social: 'Papelería y Distribuciones del Centro Sociedad Anónima Cerrada', direccion: 'Dirección que no debe aparecer en la tabla', telefono: '987654321', email: 'administracion.comercial@distribucionesdelcentro.example.test' },
  { id: 2, tipo_documento: '1', numero_documento: '12345678', razon_social: 'Ana Flores', telefono: '912345678', email: '' },
  { id: 3, tipo_documento: '6', numero_documento: '20987654321', razon_social: 'Comercial Horizonte', telefono: '', email: 'ventas@horizonte.test' },
  { id: 4, tipo_documento: '1', numero_documento: '87654321', razon_social: 'Pedro Salas', telefono: '', email: '' },
  { id: 5, tipo_documento: '6', numero_documento: '20111111111', razon_social: 'Contacto WhatsApp', telefono: '', whatsapp: '999111222', email: '' },
];

async function openDirectory(browser, baseURL, viewport) {
  const context = await browser.newContext({ baseURL, viewport, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
  await context.addInitScript(() => localStorage.setItem('token', 'clients-directory-e2e-token'));
  const page = await context.newPage();
  const calls = [];
  const unexpected = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    let payload;
    if (request.method() !== 'GET') unexpected.push(`${request.method()} ${path}`);
    else if (path === '/users/me') payload = { id: 7301, email: 'clients.e2e@inkora.test', nombre_completo: 'Operador Clientes', rol: 'admin', is_superadmin: false, must_change_password: false, tenant_id: 73 };
    else if (path === '/tenant/subscription-status') payload = {};
    else if (path === '/sunat/exchange-rate') payload = { compra: 3.7, venta: 3.72, moneda: 'USD' };
    else if (path === '/clientes/page') {
      calls.push(url);
      const segment = url.searchParams.get('segment');
      const query = (url.searchParams.get('q') || '').toLowerCase();
      const items = clients.filter((client) => (!query || client.razon_social.toLowerCase().includes(query)) && (segment === 'empresa' ? client.tipo_documento === '6' : segment === 'persona' ? client.tipo_documento === '1' : true));
      const searched = clients.filter((client) => !query || client.razon_social.toLowerCase().includes(query));
      const resultCounts = query ? { all: searched.length, empresa: searched.filter((client) => client.tipo_documento === '6').length, persona: searched.filter((client) => client.tipo_documento === '1').length, credito: 0, incompletos: searched.length } : counts;
      payload = { items, total: resultCounts[segment] ?? resultCounts.all, counts: resultCounts };
    } else unexpected.push(`${request.method()} ${path}`);
    await route.fulfill({ status: payload === undefined ? 500 : 200, contentType: 'application/json', body: JSON.stringify(payload ?? { detail: 'Solicitud no simulada' }) });
  });
  const errors = attachCriticalErrorCollector(page);
  await page.goto('/clientes');
  await expect(page.getByRole('table', { name: 'Clientes', exact: true })).toBeVisible();
  return { context, page, calls, unexpected, errors };
}

for (const width of [1440, 1024, 390, 320]) {
  test(`directorio legible a ${width}px con contactos parciales y acciones`, async ({ browser, baseURL }, testInfo) => {
    const { context, page, calls, unexpected, errors } = await openDirectory(browser, baseURL, { width, height: 960 });
    try {
      const table = page.getByRole('table', { name: 'Clientes', exact: true });
      await expect(table.getByRole('columnheader')).toHaveText(['Cliente', 'RUC / DNI', 'Contacto', 'Acciones']);
      const rows = table.locator('.client-row');
      await expect(rows).toHaveCount(5);
      await expect(rows.first().getByRole('cell')).toHaveCount(4);
      await expect(rows.first().locator('.client-main')).not.toContainText('20123456789');
      await expect(table).not.toContainText('Dirección que no debe aparecer');
      await expect(table).not.toContainText('Sin correo');
      await expect(table).not.toContainText('Sin condición');
      await expect(rows.first().locator('.client-contact__line')).toHaveText(['987654321', clients[0].email]);
      await expect(rows.nth(1).locator('.client-contact__line')).toHaveText(['912345678']);
      await expect(rows.nth(2).locator('.client-contact__line')).toHaveText(['ventas@horizonte.test']);
      await expect(rows.nth(3).locator('.client-contact')).toHaveText('-');
      await expect(rows.nth(4).locator('.client-contact__line')).toHaveText(['999111222']);
      await expect(page.locator('.stat').filter({ has: page.getByText('Empresas', { exact: true }) }).locator('.stat-value')).toHaveText('155');
      await expect(page.locator('.stat').filter({ has: page.getByText('Personas', { exact: true }) }).locator('.stat-value')).toHaveText('28');
      const nameBox = await rows.first().locator('.client-name').boundingBox();
      const pillBox = await rows.first().locator('.pill').boundingBox();
      expect(pillBox.y).toBeGreaterThanOrEqual(nameBox.y + nameBox.height);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect(await table.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
      if (width > 960) {
        const headingBox = await table.getByRole('columnheader', { name: 'RUC / DNI' }).boundingBox();
        const documentBox = await rows.first().locator('.client-document').boundingBox();
        expect(Math.abs(headingBox.x - documentBox.x)).toBeLessThan(1);
      }
      await page.screenshot({ path: testInfo.outputPath(`clientes-${width}.png`), fullPage: true });
      if (width <= 960) await rows.first().screenshot({ path: testInfo.outputPath(`cliente-contacto-${width}.png`) });

      const trigger = rows.first().getByRole('button', { name: /^Más acciones de/ });
      await trigger.click();
      const menu = page.locator('.ink-action-menu');
      await expect(menu).toBeVisible();
      const menuBox = await menu.boundingBox();
      expect(menuBox.x).toBeGreaterThanOrEqual(0);
      expect(menuBox.x + menuBox.width).toBeLessThanOrEqual(width);
      await page.keyboard.press('Escape');
      await expect(trigger).toBeFocused();
      await trigger.click();
      await menu.getByRole('button', { name: 'Eliminar cliente', exact: true }).click();
      await page.getByRole('dialog').getByRole('button', { name: 'Cancelar', exact: true }).click();
      await expect(trigger).toBeFocused();
      await rows.first().getByRole('button', { name: 'Editar', exact: true }).click();
      await expect(page.getByRole('dialog', { name: 'Editar cliente' })).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).toHaveCount(0);

      if (width === 1440) {
        await page.getByRole('button', { name: 'Empresas 155', exact: true }).click();
        await expect(rows).toHaveCount(3);
        expect(calls.at(-1).searchParams.get('segment')).toBe('empresa');
        await page.getByPlaceholder('Buscar por nombre, RUC/DNI, correo o teléfono...').fill('Horizonte');
        await expect(rows).toHaveCount(1);
        expect(calls.at(-1).searchParams.get('q')).toBe('Horizonte');
        expect(calls.at(-1).searchParams.get('segment')).toBe('empresa');
        await expect(page.locator('.stat').filter({ has: page.getByText('Empresas', { exact: true }) }).locator('.stat-value')).toHaveText('1');
      }
      expect(unexpected).toEqual([]);
      errors.assertClean();
    } finally {
      await context.close();
    }
  });
}
