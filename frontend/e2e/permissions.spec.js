import { expect, test } from '@playwright/test';

test('usuario no autenticado redirige /dashboard a /login', async ({ browser, baseURL }) => {
  const context = await browser.newContext({
    baseURL,
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();

  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/login(?:$|[?#])/);
  await expect(page.getByRole('heading', { name: /bienvenido de vuelta/i })).toBeVisible();

  await context.close();
});

test('usuario tenant no superadmin no entra a /superadmin', async ({ page }) => {
  await page.goto('/superadmin');
  await expect(page).toHaveURL(/\/dashboard(?:$|[?#])/);
  await expect(page.getByText('Superadmin').first()).not.toBeVisible();
});
