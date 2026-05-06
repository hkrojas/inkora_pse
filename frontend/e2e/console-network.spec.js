import { test } from '@playwright/test';
import {
  assertUsableRoute,
  attachApiOriginGuard,
  attachCriticalErrorCollector,
} from './helpers/assertions';
import { TENANT_STORAGE_STATE } from './helpers/auth';
import { MAIN_ROUTES } from './helpers/routes';

test.describe('rutas principales sin errores criticos', () => {
  for (const route of MAIN_ROUTES) {
    test(`${route.path} no tiene errores criticos ni API fuera del backend esperado`, async ({
      browser,
      baseURL,
    }) => {
      const context = await browser.newContext({
        baseURL,
        storageState: TENANT_STORAGE_STATE,
      });
      const page = await context.newPage();
      const routeCriticalErrors = attachCriticalErrorCollector(page);
      const routeApiOrigin = attachApiOriginGuard(page);

      try {
        await assertUsableRoute(page, route);
        routeCriticalErrors.assertClean();
        routeApiOrigin.assertClean();
      } finally {
        await context.close();
      }
    });
  }
});
