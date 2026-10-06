import { test, expect } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const apiOrigin = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const user = { id: 9, tenant_id: 74, rol: 'admin', is_active: true, is_superadmin: false, nombre_completo: 'Fiscal QA', email: 'qa@inkora.test', must_change_password: false };
const client = { id: 1, razon_social: 'Cliente QA', tipo_documento: '6', numero_documento: '20123456789', direccion: 'Av. Lima 100' };
const quote = { id: 7, serie: 'COT', correlativo: 7, document_kind: 'quotation', tipo_comprobante: '00', estado: 'pendiente', fecha_emision: '2026-09-22T09:15:00', moneda: 'PEN', total_venta: 118, saldo_pendiente: 118, condicion_pago: 'contado', cliente: client, items: [] };

async function harness(browser, baseURL, width = 1440) {
  const context = await browser.newContext({ baseURL, timezoneId: 'UTC', viewport: { width, height: 900 }, storageState: { cookies: [], origins: [] } });
  await context.addInitScript(() => localStorage.setItem('token', 'offline-date-qa'));
  const page = await context.newPage();
  await page.clock.install({ time: new Date('2026-10-07T04:45:00Z') });
  const errors = attachCriticalErrorCollector(page);
  const unexpected = [], posts = [];
  await page.route('**/*', async (route) => {
    const req = route.request(), url = new URL(req.url());
    if (!['fetch', 'xhr'].includes(req.resourceType())) {
      if (url.origin !== new URL(baseURL).origin && !['data:', 'blob:'].includes(url.protocol)) {
        unexpected.push(req.url()); await route.abort(); return;
      }
      await route.continue(); return;
    }
    const path = url.pathname.replace(/\/$/, ''), method = req.method();
    if (url.origin !== apiOrigin) { unexpected.push(req.url()); await route.abort(); return; }
    let payload, status = 200;
    if (path === '/cotizaciones/7/facturar' && method === 'POST') {
      posts.push(req.postDataJSON());
      payload = { success: true, queued: true, job_status: 'queued', job_id: 1007, resource_id: 42 };
      status = 202;
    } else if (method !== 'GET') { unexpected.push(`${method} ${path}`); await route.abort(); return; }
    else if (path === '/users/me') payload = user;
    else if (path === '/tenant') payload = { id: 74, business_name: 'Fiscal QA', business_ruc: '20999999999', is_active: true, inventory_enabled: false };
    else if (path === '/tenant/subscription-status') payload = { fiscal_feature_flags: {} };
    else if (path === '/sunat/exchange-rate') payload = { compra: 3.7, venta: 3.72 };
    else if (path === '/clientes/page') payload = { items: [client], total: 1 };
    else if (path === '/productos/page') payload = { items: [], total: 0 };
    else if (path === '/inventario/almacenes') payload = [];
    else if (path === '/inventario/documentos/7/disponibilidad') payload = { inventory_enabled: false, sufficient: true };
    else if (path === '/cotizaciones/page') payload = { items: [quote], total: 1 };
    else if (path === '/facturas-emitidas/page') payload = { items: [], total: 0, counts: { all: 0 } };
    else if (path === '/cotizaciones/7') payload = quote;
    else if (path === '/cotizaciones/7/pagos') payload = [];
    else if (path === '/facturacion/comprobantes/7/guias') payload = [];
    else { unexpected.push(`${method} ${path}`); await route.abort(); return; }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(payload) });
  });
  return { context, page, posts, clean: () => { expect(unexpected).toEqual([]); errors.assertClean(); } };
}

for (const tipo of ['01', '03']) {
  test(`nuevo ${tipo}: fecha de Perú automática y sin edición retroactiva`, async ({ browser, baseURL }, testInfo) => {
    const h = await harness(browser, baseURL, tipo === '03' ? 390 : 1440);
    try {
      await h.page.goto(`/comprobantes/nuevo?tipo=${tipo}`);
      const field = h.page.getByLabel('Fecha de emisión', { exact: true });
      await expect(field).toHaveValue('2026-10-06');
      await expect(field).toHaveAttribute('readonly', '');
      await expect(h.page.getByText('Se asigna al emitir, con la fecha actual de Perú.')).toBeVisible();
      expect(await field.evaluate((node) => node.readOnly)).toBe(true);
      await field.scrollIntoViewIfNeeded();
      await h.page.screenshot({ path: testInfo.outputPath('date-form.png') });
      h.clean();
    } finally { await h.context.close(); }
  });
}

test('cotización antigua: el listado anuncia procesamiento y muestra la fecha fiscal propia', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  try {
    await h.page.goto('/cotizaciones?view=history');
    await h.page.getByRole('button', { name: 'Emitir factura o boleta desde esta cotizacion', exact: true }).click();
    await expect(h.page.getByText('El comprobante se emitirá con la fecha actual de Perú.')).toBeVisible();
    await h.page.getByRole('button', { name: 'Emitir Factura', exact: true }).click();
    await expect(h.page.getByText('Factura enviada a procesamiento fiscal. La aceptación de SUNAT aún está pendiente.')).toBeVisible();
    expect(h.posts).toEqual([{ tipo_comprobante: '01' }]);
    await expect(h.page.getByText(/emitido correctamente/i)).toHaveCount(0);
    h.clean();
  } finally { await h.context.close(); }
});
