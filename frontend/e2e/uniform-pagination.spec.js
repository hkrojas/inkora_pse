import { expect, test } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const TOTAL = 37;

const user = {
  id: 7401,
  email: 'pagination.qa@inkora.test',
  nombre_completo: 'Pagination QA',
  rol: 'admin',
  is_superadmin: false,
  must_change_password: false,
  tenant_id: 74,
};

function fiscalDocument(index, label = `Cliente ${index}`) {
  return {
    id: index,
    serie: 'F001',
    correlativo: index,
    document_number: `F001-${String(index).padStart(6, '0')}`,
    fecha_emision: '2026-09-30T10:00:00-05:00',
    fecha_vencimiento: '2026-10-30T10:00:00-05:00',
    moneda: 'PEN',
    estado: 'pendiente',
    document_kind: 'fiscal_document',
    tipo_comprobante: '01',
    total_venta: 118,
    monto_pagado: 0,
    saldo_pendiente: 118,
    cliente: { id: index, razon_social: label, numero_documento: `20${String(index).padStart(9, '0')}` },
  };
}

function fiscalNote(index) {
  return {
    ...fiscalDocument(index, `Cliente nota ${index}`),
    document_kind: index % 2 ? 'credit_note' : 'debit_note',
    tipo_comprobante: index % 2 ? '07' : '08',
    nota_motivo_descripcion: 'Ajuste fiscal',
  };
}

function retencion(index) {
  return {
    id: index,
    serie: 'R001',
    correlativo: String(index).padStart(6, '0'),
    fecha_emision: '2026-09-30T10:00:00-05:00',
    proveedor_num_doc: `20${String(index).padStart(9, '0')}`,
    proveedor_rzn_social: `Proveedor ${index}`,
    imp_retenido: 30,
    imp_pagado: 970,
    status: 'sent',
    ticket: `T-R-${index}`,
  };
}

function percepcion(index) {
  return {
    id: index,
    serie: 'P001',
    correlativo: String(index).padStart(6, '0'),
    fecha_emision: '2026-09-30T10:00:00-05:00',
    cliente_num_doc: `20${String(index).padStart(9, '0')}`,
    cliente_rzn_social: `Cliente percepción ${index}`,
    imp_percibido: 20,
    imp_cobrado: 1020,
    status: 'sent',
    ticket: `T-P-${index}`,
  };
}

function resumen(index) {
  return {
    id: index,
    fec_resumen: '2026-09-30T00:00:00-05:00',
    correlativo: String(index).padStart(5, '0'),
    created_at: '2026-09-30T10:00:00-05:00',
    details_count: 1,
    status: 'sent',
    ticket: `T-RC-${index}`,
  };
}

function reversion(index) {
  return {
    id: index,
    fec_comunicacion: '2026-09-30T00:00:00-05:00',
    correlativo: String(index).padStart(5, '0'),
    created_at: '2026-09-30T10:00:00-05:00',
    details_count: 1,
    status: 'sent',
    ticket: `T-RR-${index}`,
  };
}

function guide(index) {
  return {
    id: index,
    serie: 'T001',
    correlativo: index,
    estado: 'borrador',
    fecha_emision: '2026-09-30T10:00:00-05:00',
    fecha_traslado: '2026-10-01T10:00:00-05:00',
    motivo_traslado: '01',
    modalidad_traslado: '02',
    llegada_direccion: `Destino ${index}`,
    destinatario_nombre: `Destinatario ${index}`,
  };
}

function pagePayload(items, url, total = TOTAL, counts = {}) {
  const skip = Number(url.searchParams.get('skip') || 0);
  const limit = Number(url.searchParams.get('limit') || 15);
  return {
    items: items.slice(skip, skip + limit),
    total,
    skip,
    limit,
    counts,
  };
}

async function openHarness(browser, baseURL) {
  const context = await browser.newContext({ baseURL, storageState: { cookies: [], origins: [] } });
  await context.addInitScript(() => localStorage.setItem('token', 'uniform-pagination-token'));
  const page = await context.newPage();
  const calls = [];
  const state = { fiscalTotal: TOTAL, delayedSearch: false };
  const documents = Array.from({ length: TOTAL }, (_, index) => fiscalDocument(index + 1));
  const notes = Array.from({ length: TOTAL }, (_, index) => fiscalNote(index + 1));
  const retenciones = Array.from({ length: TOTAL }, (_, index) => retencion(index + 1));
  const percepciones = Array.from({ length: TOTAL }, (_, index) => percepcion(index + 1));
  const resumenes = Array.from({ length: TOTAL }, (_, index) => resumen(index + 1));
  const reversiones = Array.from({ length: TOTAL }, (_, index) => reversion(index + 1));
  const guias = Array.from({ length: TOTAL }, (_, index) => guide(index + 1));

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    calls.push({ path, params: new URLSearchParams(url.searchParams), method: request.method() });
    let payload = {};

    if (/^\/cotizaciones\/\d+\/pdf\/download$/.test(path)) {
      await route.fulfill({ status: 200, contentType: 'application/pdf', headers: { 'Content-Disposition': 'attachment; filename="nota.pdf"' }, body: '%PDF-1.4\n%%EOF' });
      return;
    }
    if (path === '/users/me') payload = user;
    else if (path === '/tenant') payload = { id: 74, business_name: 'Inkora QA', business_ruc: '20123456789', is_active: true };
    else if (path === '/tenant/subscription-status') payload = { fiscal_feature_flags: { retentions: true, perceptions: true, daily_summary: true, reversions: true, guides: true, internal_transfers: true } };
    else if (path === '/sunat/exchange-rate') payload = { compra: 3.7, venta: 3.72, moneda: 'USD' };
    else if (path === '/clientes/page') payload = { items: [], total: 0, counts: {} };
    else if (path === '/cotizaciones') payload = [];
    else if (path === '/facturas-emitidas/page') {
      const q = url.searchParams.get('q') || '';
      const skip = Number(url.searchParams.get('skip') || 0);
      if (state.delayedSearch && q) await new Promise((resolve) => setTimeout(resolve, skip === 30 ? 350 : 30));
      const source = Array.from({ length: state.fiscalTotal }, (_, index) => (
        q ? fiscalDocument(index + 1, skip === 30 ? `STALE ${index + 1}` : `FILTRADO ${index + 1}`) : documents[index]
      ));
      payload = pagePayload(source, url, state.fiscalTotal, { all: state.fiscalTotal, draft: 0, emitted: 0, pending: state.fiscalTotal, rejected: 0, voided: 0 });
    } else if (path === '/notas/page') {
      payload = pagePayload(notes, url, TOTAL, { all: TOTAL, draft: 0, emitted: 0, pending: TOTAL, rejected: 0, voided: 0 });
    } else if (path === '/retenciones/page') {
      payload = pagePayload(retenciones, url, TOTAL, { all: TOTAL, sent: TOTAL, pending: 0, rejected: 0 });
    } else if (path === '/percepciones/page') {
      payload = pagePayload(percepciones, url, TOTAL, { all: TOTAL, sent: TOTAL, pending: 0, rejected: 0 });
    } else if (path === '/resumen-diario/page') {
      payload = pagePayload(resumenes, url, TOTAL, { all: TOTAL, sent: TOTAL, pending: 0, rejected: 0 });
    } else if (path === '/reversiones/page') {
      payload = pagePayload(reversiones, url, TOTAL, { all: TOTAL, sent: TOTAL, pending: 0, rejected: 0 });
    } else if (path === '/guias-remision') {
      payload = pagePayload(guias, url, TOTAL, { all: TOTAL, pending: TOTAL, smartpse: 0, transit: 0, emitted: 0, cancelled: 0, voided: 0 });
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
  });

  return { calls, context, errors: attachCriticalErrorCollector(page), page, state };
}

const routeCases = [
  ['/facturas', 'Paginación de facturas', '/facturas-emitidas/page'],
  ['/boletas', 'Paginación de boletas', '/facturas-emitidas/page'],
  ['/bajas', 'Paginación de bajas', '/facturas-emitidas/page'],
  ['/retenciones', 'Paginación de retenciones', '/retenciones/page'],
  ['/percepciones', 'Paginación de percepciones', '/percepciones/page'],
  ['/resumen-diario', 'Paginación de resúmenes diarios', '/resumen-diario/page'],
  ['/reversiones', 'Paginación de reversiones', '/reversiones/page'],
  ['/guias', 'Paginación de guías', '/guias-remision'],
];

for (const [path, ariaLabel, endpoint] of routeCases) {
  test(`${path} navega 37 registros con el paginador compartido`, async ({ browser, baseURL }) => {
    const { calls, context, errors, page } = await openHarness(browser, baseURL);
    try {
      await page.goto(path);
      const pagination = page.getByRole('navigation', { name: ariaLabel });
      await expect(pagination).toBeVisible();
      await pagination.getByRole('button', { name: 'Ir a página 2' }).click();
      await expect(pagination.getByRole('button', { name: 'Ir a página 2' })).toHaveAttribute('aria-current', 'page');
      await pagination.getByRole('button', { name: 'Ir a página 3' }).click();
      await expect(pagination.getByRole('button', { name: 'Ir a página 3' })).toHaveAttribute('aria-current', 'page');
      await expect.poll(() => calls.filter((call) => call.path === endpoint).at(-1)?.params.get('skip')).toBe('30');
      expect(calls.filter((call) => call.path === endpoint).at(-1)?.params.get('limit')).toBe('15');
      errors.assertClean();
    } finally {
      await context.close();
    }
  });
}

test('Notas pagina tanto comprobantes elegibles como historial', async ({ browser, baseURL }) => {
  const { calls, context, errors, page } = await openHarness(browser, baseURL);
  try {
    await page.goto('/notas');
    const sources = page.getByRole('navigation', { name: 'Paginación de comprobantes elegibles' });
    await sources.getByRole('button', { name: 'Ir a página 3' }).click();
    await expect.poll(() => calls.filter((call) => call.path === '/facturas-emitidas/page').at(-1)?.params.get('skip')).toBe('30');
    await page.getByRole('tab', { name: 'Historial de notas' }).click();
    for (const number of ['000001', '000002']) {
      const downloaded = page.waitForEvent('download');
      await page.getByRole('button', { name: `Descargar PDF de F001-${number}`, exact: true }).click();
      // Cross-origin headers are not exposed by this fixture: use the note's folio.
      expect((await downloaded).suggestedFilename()).toBe(`F001-${number}.pdf`);
    }
    const history = page.getByRole('navigation', { name: 'Paginación del historial de notas' });
    await history.getByRole('button', { name: 'Ir a página 3' }).click();
    await expect.poll(() => calls.filter((call) => call.path === '/notas/page').at(-1)?.params.get('skip')).toBe('30');
    errors.assertClean();
  } finally {
    await context.close();
  }
});

test('Facturas conserva la búsqueda y descarta una respuesta tardía de la página anterior', async ({ browser, baseURL }) => {
  const { calls, context, errors, page, state } = await openHarness(browser, baseURL);
  try {
    await page.goto('/facturas');
    const pagination = page.getByRole('navigation', { name: 'Paginación de facturas' });
    await pagination.getByRole('button', { name: 'Ir a página 3' }).click();
    state.delayedSearch = true;
    await page.getByPlaceholder('Buscar por serie, número o cliente...').fill('cliente');
    await expect.poll(() => calls.some((call) => call.path === '/facturas-emitidas/page' && call.params.get('q') === 'cliente' && call.params.get('skip') === '0')).toBe(true);
    await expect(pagination.getByRole('button', { name: 'Ir a página 1' })).toHaveAttribute('aria-current', 'page');
    await pagination.getByRole('button', { name: 'Ir a página 2' }).click();
    await expect.poll(() => {
      const call = calls.filter((item) => item.path === '/facturas-emitidas/page').at(-1);
      return `${call?.params.get('q')}:${call?.params.get('skip')}`;
    }).toBe('cliente:15');
    await page.waitForTimeout(400);
    await expect(page.getByText(/STALE/)).toHaveCount(0);
    errors.assertClean();
  } finally {
    await context.close();
  }
});

test('Facturas retrocede desde una última página que quedó vacía', async ({ browser, baseURL }) => {
  const { calls, context, errors, page, state } = await openHarness(browser, baseURL);
  try {
    await page.goto('/facturas');
    const pagination = page.getByRole('navigation', { name: 'Paginación de facturas' });
    await pagination.getByRole('button', { name: 'Ir a página 3' }).click();
    state.fiscalTotal = 30;
    await page.getByRole('button', { name: 'Actualizar lista' }).click();
    await expect.poll(() => calls.filter((call) => call.path === '/facturas-emitidas/page').at(-1)?.params.get('skip')).toBe('15');
    await expect(page.getByRole('navigation', { name: 'Paginación de facturas' }).getByRole('button', { name: 'Ir a página 2' })).toHaveAttribute('aria-current', 'page');
    errors.assertClean();
  } finally {
    await context.close();
  }
});
