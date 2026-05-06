import { test } from '@playwright/test';
import { assertUsableRoute } from './helpers/assertions';
import { MAIN_ROUTES } from './helpers/routes';

test.describe('navegacion principal autenticada', () => {
  for (const route of MAIN_ROUTES) {
    test(`${route.path} carga sin pantalla blanca`, async ({ page }) => {
      await assertUsableRoute(page, route);
    });
  }
});
