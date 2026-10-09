import { test, expect } from '@playwright/test';

const apiOrigin = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const original = {
  id: 31, correlativo: '20261007-00001', fec_resumen: '2026-10-07T00:00:00-05:00',
  created_at: '2026-10-07T10:00:00-05:00', updated_at: '2026-10-07T10:00:00-05:00',
  status: 'sent', success: true, ticket: 'T-SYNTHETIC', details_count: 1,
};

async function setup(browser, baseURL, { theme = 'light', result = 'sent', sendStatus = 200 } = {}) {
  const context = await browser.newContext({ baseURL, viewport: { width: 390, height: 850 }, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
  await context.addInitScript(value => {
    localStorage.setItem('token', 'offline-summary-qa');
    localStorage.setItem('inkora-theme', value);
  }, theme);
  const page = await context.newPage();
  const calls = [], unexpected = [], pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  let row = { ...original }, releaseRequest;
  const payloads = {
    '/users/me': { id: 9, tenant_id: 74, rol: 'admin', is_active: true, is_superadmin: false, nombre_completo: 'Resumen QA', must_change_password: false },
    '/tenant': { id: 74, business_name: 'Resumen QA', business_ruc: '20999999999', is_active: true, inventory_enabled: false },
    '/tenant/subscription-status': { fiscal_feature_flags: { daily_summary: true } },
    '/sunat/exchange-rate': { buy: 3.7, sell: 3.72 },
  };
  await page.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname.replace(/\/$/, '');
    if (!['fetch', 'xhr'].includes(request.resourceType())) {
      if (url.origin === new URL(baseURL).origin || ['data:', 'blob:'].includes(url.protocol)) await route.continue();
      else { unexpected.push(request.url()); await route.abort(); }
      return;
    }
    const fulfill = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.origin === apiOrigin && request.method() === 'GET') {
      if (path === '/resumen-diario/page') {
        return fulfill({ items: [row], total: 1, counts: { all: 1, sent: Number(row.status === 'sent'), pending: Number(row.status === 'pending'), rejected: Number(row.status === 'rejected') } });
      }
      if (payloads[path]) return fulfill(payloads[path]);
    }
    if (url.origin === apiOrigin && request.method() === 'POST' && ['/resumen-diario/31/consultar', '/resumen-diario/enviar'].includes(path)) {
      calls.push({ path, payload: request.postDataJSON() });
      await new Promise(resolve => { releaseRequest = resolve; });
      row = { ...row, status: result, success: result === 'sent', updated_at: '2026-10-07T11:00:00-05:00', sunat_error: result === 'rejected' ? 'SUNAT 2335: rechazo sintético' : null };
      return fulfill(sendStatus >= 500 ? { detail: 'Respuesta pendiente sintética' } : row, sendStatus);
    }
    unexpected.push(`${request.method()} ${url.pathname}`); await route.abort();
  });
  await page.goto('/resumen-diario');
  await expect(page.getByText('Enviado · consultar estado', { exact: true })).toBeVisible();
  return { context, page, calls, unexpected, pageErrors, release: () => releaseRequest() };
}

for (const theme of ['light', 'dark']) {
  for (const result of ['sent', 'pending', 'rejected']) {
    test(`resumen ${theme}: consulta ${result} sin reenviar ni duplicar solicitudes`, async ({ browser, baseURL }, testInfo) => {
      const qa = await setup(browser, baseURL, { theme, result });
      try {
        const consult = qa.page.getByRole('button', { name: 'Consultar estado de RC-20261007-00001', exact: true });
        await consult.click();
        await expect.poll(() => qa.calls.length).toBe(1);
        await expect(consult).toBeDisabled();
        await qa.page.keyboard.press('Enter');
        expect(qa.calls).toHaveLength(1);
        qa.release();
        const label = { sent: 'Aceptado', pending: 'Pendiente de confirmación', rejected: 'Rechazado' }[result];
        await expect(qa.page.locator('.summary-status-actions').getByText(label, { exact: true })).toBeVisible();
        if (result !== 'sent') await expect(qa.page.getByText('Resumen aceptado por SUNAT.', { exact: true })).toHaveCount(0);
        for (const width of [320, 390, 1440]) {
          await qa.page.setViewportSize({ width, height: 850 });
          await consult.scrollIntoViewIfNeeded();
          await expect.poll(() => qa.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
          const box = await consult.boundingBox();
          expect(box.x).toBeGreaterThanOrEqual(0);
          expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
          if (width <= 768) expect(box.height).toBeGreaterThanOrEqual(44);
          await qa.page.screenshot({ path: testInfo.outputPath(`${result}-${theme}-${width}.png`), animations: 'disabled' });
        }
        expect(qa.calls.map(call => call.path)).toEqual(['/resumen-diario/31/consultar']);
        expect(qa.unexpected).toEqual([]); expect(qa.pageErrors).toEqual([]);
      } finally { await qa.context.close(); }
    });
  }
}

for (const sendStatus of [200, 502]) {
  test(`envío ${sendStatus}: un ticket o error ambiguo no afirma aceptación ni reenvía`, async ({ browser, baseURL }) => {
    const qa = await setup(browser, baseURL, { result: 'pending', sendStatus });
    try {
      await qa.page.getByRole('button', { name: 'Nuevo resumen', exact: true }).click();
      const form = qa.page.locator('#resumen-diario-form');
      await form.getByPlaceholder('B001-000001', { exact: true }).fill('B001-1');
      const state = form.locator('.ink-select-trigger').first();
      await state.click();
      await expect(qa.page.getByRole('option', { name: '2 - Modificar', exact: true })).toBeVisible();
      await qa.page.getByRole('option', { name: '3 - Anular', exact: true }).click();
      await form.getByPlaceholder('00000000', { exact: true }).fill('12345678');
      const amounts = form.getByPlaceholder('0.00', { exact: true });
      await amounts.nth(0).fill('118'); await amounts.nth(1).fill('100'); await amounts.nth(2).fill('18');
      const send = qa.page.getByRole('button', { name: 'Enviar resumen', exact: true });
      await send.click();
      await expect.poll(() => qa.calls.length).toBe(1);
      await expect(send).toBeDisabled();
      expect(qa.calls[0].payload.details[0].estado).toBe('3');
      qa.release();
      await expect(form).toHaveCount(0);
      await expect(qa.page.locator('.summary-status-actions').getByText('Pendiente de confirmación', { exact: true })).toBeVisible();
      await expect(qa.page.getByText('Resumen aceptado por SUNAT.', { exact: true })).toHaveCount(0);
      expect(qa.calls.map(call => call.path)).toEqual(['/resumen-diario/enviar']);
      expect(qa.unexpected).toEqual([]); expect(qa.pageErrors).toEqual([]);
    } finally { await qa.context.close(); }
  });
}
