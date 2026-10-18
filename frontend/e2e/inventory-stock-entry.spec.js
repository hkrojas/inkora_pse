import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { attachApiOriginGuard, attachCriticalErrorCollector } from './helpers/assertions';
import { chooseInkoraOption, expectPopupWithinViewport } from './helpers/inkora-controls';

const API_URL = process.env.E2E_API_URL || 'http://localhost:8000';

for (const width of [1440, 390]) {
  test(`+ Stock carga en otro almacén sin saldo previo y conserva el origen a ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 960 });
    const errors = attachCriticalErrorCollector(page);
    const originGuard = attachApiOriginGuard(page);
    const storage = await page.context().storageState();
    const token = storage.origins.flatMap((origin) => origin.localStorage).find((entry) => entry.name === 'token')?.value;
    expect(token).toBeTruthy();
    const headers = { Authorization: `Bearer ${token}` };
    const api = async (method, path, data) => {
      const response = await page.request[method](`${API_URL}${path}`, { headers, data });
      expect(response.ok(), `${method.toUpperCase()} ${path}: ${response.status()}`).toBe(true);
      return response.json();
    };
    const suffix = randomUUID().slice(0, 8);
    const productName = `Papel stock QA ${suffix}`;
    const destinationName = `Casa QA ${suffix}`;
    const source = await api('post', '/inventario/activar', {});
    const destination = await api('post', '/inventario/almacenes', { code: `QA-${suffix}`, name: destinationName });
    const product = await api('post', '/productos/', { nombre: productName, codigo_interno: `STK-${suffix}`, precio_unitario: '1.18' });
    await api('put', `/inventario/productos/${product.id}`, {
      item_type: 'inventory', inventory_enabled: true, warehouse_id: source.id, opening_stock: 3500, minimum_stock: 0,
    });
    const productStock = async () => (await api('get', '/inventario/existencias')).filter((row) => row.product_id === product.id);
    expect(await productStock()).toHaveLength(1);

    await page.goto('/inventario');
    await page.getByPlaceholder('Buscar producto, SKU o almacén').fill(productName);
    const rows = page.locator('.inventory-stock-row:visible, .inventory-stock-card:visible').filter({ hasText: productName });
    await expect(rows).toHaveCount(1);
    await rows.getByRole('button', { name: 'Stock', exact: true }).click();
    const drawer = page.getByRole('dialog', { name: 'Agregar existencias', exact: true });
    const actual = drawer.locator('dl div').filter({ has: page.getByText('Stock actual', { exact: true }) }).locator('dd');
    const projected = drawer.locator('dl div').filter({ has: page.getByText('Después del ingreso', { exact: true }) }).locator('dd');
    await expect(drawer.getByRole('button', { name: 'Almacén de destino', exact: true })).toHaveText(source.name);
    await expect(actual).toHaveText('3,500');
    const quantity = drawer.getByLabel('Unidades a agregar');
    await quantity.fill('25.5');
    await drawer.getByRole('button', { name: 'Almacén de destino', exact: true }).click();
    const popup = page.getByRole('listbox', { name: 'Almacén de destino', exact: true });
    await expectPopupWithinViewport(page, popup);
    await popup.getByRole('option', { name: destinationName, exact: true }).click();
    await expect(drawer.getByRole('heading', { name: productName, exact: true })).toBeVisible();
    await expect(actual).toHaveText('0');
    await expect(projected).toHaveText('25.5');
    await expect(quantity).toHaveValue('25.5');
    await chooseInkoraOption(page, 'Almacén de destino', source.name);
    await expect(actual).toHaveText('3,500');
    await expect(projected).toHaveText('3,525.5');
    await chooseInkoraOption(page, 'Almacén de destino', destinationName);
    const submit = drawer.getByRole('button', { name: 'Agregar al stock', exact: true });
    await quantity.fill('0');
    await expect(submit).toBeDisabled();
    await quantity.fill('-1');
    await expect(submit).toBeDisabled();
    await quantity.fill('25.5');
    const screenshotPath = testInfo.outputPath(`stock-destino-${width}.png`);
    await drawer.screenshot({ path: screenshotPath });
    await testInfo.attach(`stock-destino-${width}`, { path: screenshotPath, contentType: 'image/png' });
    const saved = page.waitForResponse((response) => new URL(response.url()).pathname === '/inventario/ajustes' && response.request().method() === 'POST');
    await submit.click();
    const response = await saved;
    expect(response.ok()).toBe(true);
    expect(response.request().postDataJSON()).toMatchObject({ warehouse_id: destination.id, product_id: product.id, quantity: 25.5 });
    await expect(drawer).toHaveCount(0);
    await expect(rows).toHaveCount(2);
    let balances = await productStock();
    expect(Number(balances.find((row) => row.warehouse_id === source.id).on_hand)).toBe(3500);
    expect(Number(balances.find((row) => row.warehouse_id === destination.id).on_hand)).toBe(25.5);

    await rows.filter({ hasText: destinationName }).getByRole('button', { name: 'Stock', exact: true }).click();
    await expect(actual).toHaveText('25.5');
    await quantity.fill('10');
    await expect(projected).toHaveText('35.5');
    await submit.click();
    await expect(drawer).toHaveCount(0);
    await page.reload();
    await expect(rows).toHaveCount(2);
    balances = await productStock();
    expect(Number(balances.find((row) => row.warehouse_id === source.id).on_hand)).toBe(3500);
    expect(Number(balances.find((row) => row.warehouse_id === destination.id).on_hand)).toBe(35.5);
    const movements = await api('get', `/inventario/kardex?product_id=${product.id}&warehouse_id=${destination.id}`);
    expect(movements).toHaveLength(2);
    expect(movements.every((movement) => movement.product_id === product.id && movement.warehouse_id === destination.id)).toBe(true);
    errors.assertClean();
    originGuard.assertClean();
  });
}
