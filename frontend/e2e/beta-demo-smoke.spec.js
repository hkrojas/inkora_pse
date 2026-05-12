import { expect, test } from '@playwright/test';
import {
  assertUsableRoute,
  attachApiOriginGuard,
  attachCriticalErrorCollector,
} from './helpers/assertions';
import { API_URL, MAIN_ROUTES } from './helpers/routes';

const FISCAL_MUTATION_PATH = /\/(emitir|anular|bajas|resumen-diario|reversiones|retenciones|percepciones)(?:\/|$)/i;
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

function attachFiscalMutationGuard(page) {
  const apiOrigin = new URL(API_URL).origin;
  const fiscalMutations = [];

  page.on('request', (request) => {
    if (!MUTATING_METHODS.has(request.method())) return;
    const url = new URL(request.url());
    if (url.origin !== apiOrigin) return;
    if (!FISCAL_MUTATION_PATH.test(url.pathname)) return;
    fiscalMutations.push(`${request.method()} ${url.pathname}`);
  });

  return {
    assertClean() {
      expect(fiscalMutations).toEqual([]);
    },
    fiscalMutations,
  };
}

test.describe('demo beta prepago sin SUNAT real', () => {
  test('tenant recorre el launch scope sin errores criticos ni mutaciones fiscales', async ({ page }) => {
    const criticalErrors = attachCriticalErrorCollector(page);
    const apiOriginGuard = attachApiOriginGuard(page);
    const fiscalMutationGuard = attachFiscalMutationGuard(page);

    for (const route of MAIN_ROUTES) {
      await test.step(`${route.path} carga`, async () => {
        await assertUsableRoute(page, route);
      });
    }

    criticalErrors.assertClean();
    apiOriginGuard.assertClean();
    fiscalMutationGuard.assertClean();
  });
});
