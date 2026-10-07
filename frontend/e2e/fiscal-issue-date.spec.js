import { test, expect } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const apiOrigin = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const user = { id: 9, tenant_id: 74, rol: 'admin', is_active: true, is_superadmin: false, nombre_completo: 'Fiscal QA', email: 'qa@inkora.test', must_change_password: false };
const client = { id: 1, razon_social: 'CLIENTE QA', tipo_documento: '6', numero_documento: '20191308868', direccion: 'AV. LIMA 100', ubigeo: '150101' };
const quote = { id: 7, serie: 'COT', correlativo: 7, document_kind: 'quotation', tipo_comprobante: '00', estado: 'pendiente', fecha_emision: '2026-09-22T09:15:00', moneda: 'PEN', total_venta: 118, saldo_pendiente: 118, condicion_pago: 'contado', cliente: client, items: [] };

async function harness(browser, baseURL, width = 1440) {
  const context = await browser.newContext({ baseURL, timezoneId: 'UTC', viewport: { width, height: 900 }, storageState: { cookies: [], origins: [] } });
  await context.addInitScript(() => localStorage.setItem('token', 'offline-date-qa'));
  const page = await context.newPage();
  await page.clock.install({ time: new Date('2026-10-07T04:45:00Z') });
  const errors = attachCriticalErrorCollector(page);
  const unexpected = [], posts = [], creations = [];
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
    } else if (method === 'POST' && path === '/clientes') payload = client;
    else if (method === 'POST' && path === '/productos') payload = { id: 10, nombre: 'SERVICIO QA', codigo_interno: 'QA001', precio_unitario: 118, unidad_medida: 'NIU', tipo_afectacion_igv: '10' };
    else if (method === 'POST' && path === '/cotizaciones') { creations.push(req.postDataJSON()); payload = quote; }
    else if (method !== 'GET') { unexpected.push(`${method} ${path}`); await route.abort(); return; }
    else if (path === '/users/me') payload = user;
    else if (path === '/tenant') payload = { id: 74, business_name: 'Fiscal QA', business_ruc: '20999999999', is_active: true, inventory_enabled: false };
    else if (path === '/tenant/subscription-status') payload = { fiscal_feature_flags: {} };
    else if (path === '/sunat/exchange-rate') payload = { compra: 3.7, venta: 3.72 };
    else if (path === '/clientes/page') payload = { items: [client], total: 1 };
    else if (path === '/clientes/search' || path === '/productos/search') payload = [];
    else if (path === '/productos/page') payload = { items: [], total: 0 };
    else if (path === '/inventario/almacenes') payload = [];
    else if (path === '/inventario/documentos/7/disponibilidad') payload = { inventory_enabled: false, sufficient: true };
    else if (path === '/cotizaciones/page') payload = { items: [quote], total: 1 };
    else if (path === '/facturas-emitidas/page') payload = { items: [], total: 0, counts: { all: 0 } };
    else if (path === '/cotizaciones/7') payload = quote;
    else if (path === '/cotizaciones/7/pagos') payload = [];
    else if (path === '/cotizaciones/42') payload = { ...quote, id: 42, source_quote_id: 7, document_kind: 'fiscal_document', tipo_comprobante: posts[0]?.tipo_comprobante || '01' };
    else if (path === '/cotizaciones/42/pagos') payload = [];
    else if (path === '/facturacion/comprobantes/42/guias') payload = [];
    else if (path === '/facturas-emitidas/42/acciones') payload = { retry_emission: false, retry_block_reason: 'Resultado fiscal pendiente', job_id: 1007, job_status: 'queued', job_action: 'emit_fiscal_document' };
    else if (path === '/emission-jobs/1007') payload = { id: 1007, resource_id: 42, status: 'queued', action: 'emit_fiscal_document', updated_at: '2026-10-06T23:45:00-05:00' };
    else if (path === '/facturacion/comprobantes/7/guias') payload = [];
    else { unexpected.push(`${method} ${path}`); await route.abort(); return; }
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(payload) });
  });
  return { context, page, posts, creations, clean: () => { expect(unexpected).toEqual([]); errors.assertClean(); } };
}

for (const tipo of ['01', '03']) {
  test(`nuevo ${tipo}: fecha elegible dentro del plazo individual de SUNAT`, async ({ browser, baseURL }, testInfo) => {
    const h = await harness(browser, baseURL, tipo === '03' ? 390 : 1440);
    try {
      await h.page.goto(`/comprobantes/nuevo?tipo=${tipo}`);
      const field = h.page.getByLabel('Fecha de emisión', { exact: true });
      await expect(field).toHaveValue('2026-10-06');
      const chosen = tipo === '03' ? '2026-10-01' : '2026-10-03';
      await expect(field).toHaveAttribute('min', chosen);
      await expect(field).toHaveAttribute('max', '2026-10-06');
      expect(await field.evaluate((node) => node.readOnly)).toBe(false);
      await field.fill(chosen);
      await expect(field).toHaveValue(chosen);
      await h.page.getByRole('textbox', { name: 'Número de documento', exact: true }).fill(client.numero_documento);
      await h.page.getByRole('textbox', { name: 'Razón social o nombre', exact: true }).fill(client.razon_social);
      await h.page.getByRole('textbox', { name: 'Dirección fiscal', exact: true }).fill(client.direccion);
      await h.page.getByRole('textbox', { name: 'Ubigeo', exact: true }).fill(client.ubigeo);
      await h.page.getByRole('textbox', { name: 'Producto o descripción', exact: true }).fill('SERVICIO QA');
      await h.page.getByPlaceholder('0.00', { exact: true }).fill('118');
      await h.page.getByRole('button', { name: tipo === '03' ? 'Emitir boleta' : 'Emitir factura', exact: true }).click();
      await expect(h.page.getByText(`Fecha de emisión: ${tipo === '03' ? '1' : '3'}/10/2026`, { exact: true })).toBeVisible();
      const actionsReady = h.page.waitForResponse((response) => new URL(response.url()).pathname === '/facturas-emitidas/42/acciones');
      const jobReady = h.page.waitForResponse((response) => new URL(response.url()).pathname === '/emission-jobs/1007');
      await h.page.getByRole('button', { name: 'Emitir comprobante', exact: true }).click();
      await actionsReady;
      await jobReady;
      await expect.poll(() => h.posts.length).toBe(1);
      expect(h.posts[0].fecha_emision).toBe(chosen);
      expect(h.creations[0].cliente_id).toBe(1);
      expect(h.creations[0].fecha_emision).toBe(`${chosen}T00:00:00-05:00`);
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

test('una fecha vencida se bloquea; cambiar boleta a factura revalida su propio plazo', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  try {
    await h.page.goto('/comprobantes/nuevo?tipo=03');
    const field = h.page.getByLabel('Fecha de emisión', { exact: true });
    await field.fill('2026-10-01');
    await h.page.getByRole('tab', { name: 'F Factura', exact: true }).click();
    await expect(field).toHaveAttribute('min', '2026-10-03');
    await expect(field).toHaveValue('2026-10-01');
    await expect(h.page.getByRole('button', { name: 'Emitir factura', exact: true })).toBeDisabled();
    expect(h.posts).toEqual([]);
    h.clean();
  } finally { await h.context.close(); }
});
