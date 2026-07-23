import { expect, test } from '@playwright/test';

const viewports = [
  { width: 360, height: 800 },
  { width: 768, height: 900 },
  { width: 1440, height: 900 },
];

for (const viewport of viewports) {
  test(`landing pública es usable a ${viewport.width}px`, async ({ browser, baseURL }) => {
    const context = await browser.newContext({ baseURL, viewport, storageState: { cookies: [], origins: [] } });
    const page = await context.newPage();
    const apiRequests = [];
    page.on('request', (request) => {
      if (request.url().includes('/api/') || request.url().includes('/facturacion/')) apiRequests.push(request.url());
    });

    try {
      await page.goto('/');

      await expect(page.getByRole('heading', { level: 1, name: /vender es difícil/i })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Solicitar acceso' }).first()).toHaveAttribute('href', '/solicitar-acceso');
      await expect(page.getByRole('link', { name: 'Iniciar sesión' }).first()).toHaveAttribute('href', '/login');
      await expect(page.getByRole('heading', { name: 'Tus clientes también merecen claridad.' })).toBeVisible();
      await expect(page.getByText('Esta función aún no recibe ni consulta datos.')).toBeVisible();

      const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
      expect(hasHorizontalOverflow).toBe(false);
      expect(apiRequests).toEqual([]);
    } finally {
      await context.close();
    }
  });
}

test('menú móvil expone navegación y accesos', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, viewport: { width: 360, height: 800 }, storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();

  try {
    await page.goto('/');
    await page.getByRole('button', { name: 'Abrir menú' }).click();
    await expect(page.getByRole('navigation', { name: 'Navegación principal' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cerrar menú' })).toHaveAttribute('aria-expanded', 'true');
  } finally {
    await context.close();
  }
});
