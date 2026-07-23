import { expect, test } from '@playwright/test';

const viewports = [
  { width: 360, height: 800 },
  { width: 768, height: 900 },
  { width: 1440, height: 900 },
];

for (const viewport of viewports) {
  test(`la entrada pública muestra el login a ${viewport.width}px`, async ({ browser, baseURL }) => {
    const context = await browser.newContext({
      baseURL,
      viewport,
      storageState: { cookies: [], origins: [] },
    });
    const page = await context.newPage();

    try {
      await page.goto('/');

      await expect(page).toHaveURL(/\/login$/);
      await expect(page.getByRole('heading', { name: 'Bienvenido de vuelta' })).toBeVisible();
      await expect(page.getByLabel('Correo / Usuario')).toBeVisible();
      await expect(page.getByPlaceholder('Ingresa tu clave')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Acceder al dashboard' })).toBeVisible();

      const hasHorizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(hasHorizontalOverflow).toBe(false);
    } finally {
      await context.close();
    }
  });
}
