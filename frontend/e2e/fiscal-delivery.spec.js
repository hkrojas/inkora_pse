import { expect, test } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
// A fresh Vite installation can pre-optimize the first document route.
test.setTimeout(60000);
const user = { id: 9, tenant_id: 74, rol: 'admin', is_active: true, is_superadmin: false, nombre_completo: 'Fiscal QA', email: 'qa@inkora.test', must_change_password: false };
const tenant = { id: 74, business_name: 'Fiscal QA', business_ruc: '20999999999', is_active: true };
const document = (id = 42) => ({ id, source_quote_id: 7, document_kind: 'fiscal_document', tipo_comprobante: '01', serie: 'F001', correlativo: id, document_number: `F001-${String(id).padStart(6, '0')}`, estado: 'pendiente', fiscal_status: 'pending_confirmation', provider_verification_status: 'signed_pending', has_deliverable_fiscal_xml: false, has_sunat_xml: false, has_sunat_cdr: false, total_venta: 118, total_igv: 18, monto_pagado: 0, saldo_pendiente: 118, moneda: 'PEN', fecha_emision: '2026-10-05', cliente: { id: 1, razon_social: 'Cliente QA', numero_documento: '20123456789' }, items: [] });

async function harness(browser, baseURL, options = {}) {
  const context = await browser.newContext({ baseURL, storageState: { cookies: [], origins: [] } });
  await context.addInitScript(() => localStorage.setItem('token', 'offline-fiscal-delivery-token'));
  const page = await context.newPage();
  await page.clock.install();
  const errors = attachCriticalErrorCollector(page);
  const state = { doc: document(), status: 'pending_confirmation', revision: 1, calls: [], unexpected: [], rows: options.rows || 1, mismatched: false, blocked: false, delayLinked: null, failRefresh: false, failRoute8: false };
  await page.route('**/*', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (!['fetch', 'xhr'].includes(req.resourceType())) {
      if (url.origin !== new URL(baseURL).origin && !['data:', 'blob:'].includes(url.protocol)) {
        state.unexpected.push(req.url()); await route.abort(); return;
      }
      await route.continue(); return;
    }
    const path = url.pathname.replace(/\/$/, '');
    state.calls.push({ path, method: req.method() });
    let payload;
    if (url.origin !== API_ORIGIN || req.method() !== 'GET') {
      state.unexpected.push(`${req.method()} ${req.url()}`); await route.abort(); return;
    }
    if (path === '/users/me') payload = user;
    else if (path === '/tenant') payload = tenant;
    else if (path === '/tenant/subscription-status') payload = { fiscal_feature_flags: {} };
    else if (path === '/sunat/exchange-rate') payload = { compra: 3.7, venta: 3.72 };
    else if (path === '/cotizaciones/7') payload = { ...document(7), document_kind: 'quotation', serie: 'COT', fiscal_status: null, linked_fiscal_document_id: 42, linked_fiscal_document_number: 'F001-000042' };
    else if (/^\/cotizaciones\/\d+\/pagos$/.test(path)) payload = [];
    else if (path === '/cotizaciones/42') {
      if (state.delayLinked) await state.delayLinked;
      if (state.failRefresh) {
        state.failRefresh = false;
        await route.fulfill({ status: 200, contentType: 'application/json', body: 'invalid-json-for-refresh-test' }); return;
      }
      if (state.blocked) { await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Documento sin acceso' }) }); return; }
      payload = { ...state.doc, source_quote_id: state.mismatched ? 8 : 7 };
    } else if (path === '/cotizaciones/8') {
      if (state.failRoute8) { await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Documento sin acceso' }) }); return; }
      payload = { ...document(8), document_kind: 'quotation', serie: 'OTHER', fiscal_status: null };
    }
    else if (/^\/facturacion\/comprobantes\/\d+\/guias$/.test(path)) payload = [];
    else if (/^\/facturas-emitidas\/\d+\/acciones$/.test(path)) {
      const id = Number(path.split('/')[2]);
      payload = { retry_emission: false, retry_block_reason: 'Resultado fiscal pendiente', job_id: 1000 + id, job_status: state.status, job_action: 'emit_fiscal_document' };
    } else if (/^\/emission-jobs\/\d+$/.test(path)) {
      const resourceId = Number(path.split('/')[2]) - 1000;
      payload = { id: 1000 + resourceId, resource_id: resourceId, status: state.status, action: 'emit_fiscal_document', updated_at: `2026-10-05T12:00:${String(state.revision).padStart(2, '0')}` };
    } else if (path === '/facturas-emitidas/page') {
      const items = Array.from({ length: state.rows }, (_, i) => ({ ...state.doc, id: 42 + i, correlativo: 42 + i }));
      payload = { items, total: items.length, counts: { all: items.length, pending: items.length, emitted: 0 } };
    } else if (path === '/cotizaciones/42/pdf/download') {
      await route.fulfill({ status: 200, contentType: 'application/pdf', headers: { 'Content-Disposition': 'attachment; filename="F001-000042.pdf"' }, body: '%PDF-1.4\n%offline fixture\n%%EOF' }); return;
    } else {
      state.unexpected.push(`${req.method()} ${req.url()}`); await route.abort(); return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
  });
  const count = (path) => state.calls.filter((call) => call.path === path).length;
  const clean = () => {
    expect(state.unexpected).toEqual([]);
    if (state.failRoute8) expect(errors.errors.filter((error) => !/console.error: Failed to load resource:.*404/.test(error))).toEqual([]);
    else errors.assertClean();
  };
  return { context, page, state, count, clean };
}

test('cotización vinculada entrega PDF firmado antes CDR y se actualiza al aceptar', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  try {
    await h.page.goto('/cotizaciones/7');
    await expect.poll(() => h.count('/emission-jobs/1042')).toBeGreaterThan(0);
    await expect(h.page.getByText('Estado fiscal: PROCESANDO', { exact: true })).toBeVisible();
    await expect(h.page.getByRole('button', { name: 'Descargar PDF de F001-000042' })).toHaveCount(0);
    await expect(h.page.getByText(/✓/)).toHaveCount(0);
    h.state.doc.has_deliverable_fiscal_xml = true;
    h.state.doc.has_sunat_xml = true;
    h.state.revision++;
    await h.page.clock.runFor(31000);
    const pdf = h.page.getByRole('button', { name: 'Descargar PDF de F001-000042' });
    await expect(pdf).toBeVisible();
    await expect(h.page.getByText('Estado fiscal: PROCESANDO', { exact: true })).toBeVisible();
    const download = h.page.waitForEvent('download');
    await pdf.click();
    expect((await download).suggestedFilename()).toBe('F001-000042.pdf');
    h.state.status = 'succeeded'; h.state.revision++;
    Object.assign(h.state.doc, { estado: 'facturada', fiscal_status: 'emitted', provider_verification_status: 'verified', has_sunat_cdr: true, sunat_accepted: true });
    await h.page.clock.runFor(31000);
    await expect(h.page.getByText('Estado fiscal: ACEPTADO', { exact: true })).toBeVisible();
    await h.page.getByRole('button', { name: 'Más acciones de F001-000042' }).click();
    await expect(h.page.getByRole('button', { name: 'Descargar CDR' })).toBeVisible();
    h.clean();
  } finally { await h.context.close(); }
});

test('pending_confirmation arranca seguimiento al abrir el fiscal', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  try {
    await h.page.goto('/cotizaciones/42');
    await expect.poll(() => h.count('/emission-jobs/1042')).toBeGreaterThan(0);
    await expect(h.page.getByText('Estado fiscal: PROCESANDO', { exact: true })).toBeVisible();
    h.clean();
  } finally { await h.context.close(); }
});

test('respuestas repetidas y cambios rápidos limitan recargas; terminal no espera cooldown', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  h.state.status = 'processing';
  try {
    await h.page.goto('/cotizaciones/42');
    await expect.poll(() => h.count('/cotizaciones/42')).toBeGreaterThanOrEqual(3);
    const initialLoads = h.count('/cotizaciones/42');
    await h.page.clock.runFor(5100);
    await expect.poll(() => h.count('/emission-jobs/1042')).toBeGreaterThanOrEqual(2);
    expect(h.count('/cotizaciones/42')).toBe(initialLoads);
    h.state.revision++;
    await h.page.clock.runFor(5100);
    await expect.poll(() => h.count('/emission-jobs/1042')).toBeGreaterThanOrEqual(3);
    expect(h.count('/cotizaciones/42')).toBe(initialLoads);
    h.state.status = 'succeeded';
    Object.assign(h.state.doc, { estado: 'facturada', fiscal_status: 'emitted', provider_verification_status: 'verified', has_sunat_cdr: true });
    await h.page.clock.runFor(5100);
    await expect(h.page.getByText('Estado fiscal: ACEPTADO', { exact: true })).toBeVisible();
    expect(h.count('/cotizaciones/42')).toBe(initialLoads + 1);
    await h.page.clock.runFor(31000);
    expect(h.count('/cotizaciones/42')).toBe(initialLoads + 1);
    h.clean();
  } finally { await h.context.close(); }
});

test('quince filas agrupan la recarga inicial sin bucle', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL, { rows: 15 });
  try {
    await h.page.goto('/facturas');
    await expect(h.page.locator('.fiscal-actions')).toHaveCount(15);
    await expect.poll(() => h.state.calls.filter((c) => c.path.startsWith('/emission-jobs/')).length).toBeGreaterThanOrEqual(15);
    await expect.poll(() => h.count('/facturas-emitidas/page')).toBeGreaterThanOrEqual(2);
    await h.page.clock.runFor(31000);
    expect(h.count('/facturas-emitidas/page')).toBeLessThanOrEqual(3);
    h.clean();
  } finally { await h.context.close(); }
});

test('una recarga terminal fallida se reintenta antes de marcarla completada', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  h.state.status = 'processing';
  try {
    await h.page.goto('/cotizaciones/42');
    await expect.poll(() => h.count('/cotizaciones/42')).toBeGreaterThanOrEqual(3);
    h.state.failRefresh = true;
    h.state.status = 'succeeded';
    Object.assign(h.state.doc, { estado: 'facturada', fiscal_status: 'emitted', provider_verification_status: 'verified', has_sunat_cdr: true });
    await h.page.clock.runFor(5100);
    await expect(h.page.getByText('No se pudo cargar la cotización. Revisa tu conexión e inténtalo nuevamente.', { exact: true })).toBeVisible();
    await expect(h.page.getByText('Estado fiscal: PROCESANDO', { exact: true })).toBeVisible();
    await h.page.clock.runFor(31000);
    await expect(h.page.getByText('Estado fiscal: ACEPTADO', { exact: true })).toBeVisible();
    const loaded = h.count('/cotizaciones/42');
    await h.page.clock.runFor(31000);
    expect(h.count('/cotizaciones/42')).toBe(loaded);
    h.clean();
  } finally { await h.context.close(); }
});

test('un vínculo inconsistente no habilita acciones fiscales ni aceptación', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  h.state.mismatched = true;
  try {
    await h.page.goto('/cotizaciones/7');
    await expect(h.page.getByRole('alert')).toContainText('No se pudo verificar el comprobante vinculado');
    await expect(h.page.locator('.fiscal-actions')).toHaveCount(0);
    await expect(h.page.getByText(/Estado fiscal: ACEPTADO|✓/)).toHaveCount(0);
    expect(h.count('/facturas-emitidas/42/acciones')).toBe(0);
    h.clean();
  } finally { await h.context.close(); }
});

test('respuesta tardía del vínculo no reemplaza el detalle de otra ruta', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  let release;
  h.state.delayLinked = new Promise((resolve) => { release = resolve; });
  try {
    await h.page.goto('/cotizaciones/7');
    await expect.poll(() => h.count('/cotizaciones/42')).toBe(1);
    // SPA navigation uses the actual router and preserves the mounted detail.
    await h.page.evaluate(() => { window.history.pushState({}, '', '/cotizaciones/8'); window.dispatchEvent(new PopStateEvent('popstate')); });
    await expect(h.page.getByRole('heading', { name: 'F001-000008' })).toBeVisible();
    release();
    await expect(h.page.locator('.fiscal-actions')).toHaveCount(0);
    expect(h.count('/facturas-emitidas/42/acciones')).toBe(0);
    h.clean();
  } finally { release(); await h.context.close(); }
});

test('ruta nueva sin acceso no conserva datos ni acciones del documento anterior', async ({ browser, baseURL }) => {
  const h = await harness(browser, baseURL);
  try {
    await h.page.goto('/cotizaciones/7');
    await expect(h.page.locator('.fiscal-actions')).toHaveCount(1);
    h.state.failRoute8 = true;
    await h.page.evaluate(() => { window.history.pushState({}, '', '/cotizaciones/8'); window.dispatchEvent(new PopStateEvent('popstate')); });
    await expect(h.page.getByText('Cotizacion no encontrada.', { exact: true })).toBeVisible();
    await expect(h.page.locator('.fiscal-actions')).toHaveCount(0);
    await expect(h.page.getByRole('heading', { name: 'F001-000007' })).toHaveCount(0);
    await expect(h.page.getByRole('link', { name: 'F001-000042', exact: true })).toHaveCount(0);
    h.clean();
  } finally { await h.context.close(); }
});
