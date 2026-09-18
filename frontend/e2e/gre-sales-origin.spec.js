import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

const API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000';

const tenant = {
  id: 8,
  business_name: 'EMPRESA DEMO GRE',
  business_ruc: '20123456789',
  business_address: 'Av. Origen 100',
  is_active: true,
};

const user = {
  id: 801,
  email: 'gre.e2e@inkora.test',
  nombre_completo: 'Operador GRE',
  rol: 'admin',
  is_superadmin: false,
  tenant_id: tenant.id,
};

const documents = {
  527: { id: 527, tipo_comprobante: '01', serie: 'F001', correlativo: 178, cliente_nombre: 'Cliente Factura' },
  528: { id: 528, tipo_comprobante: '03', serie: 'B001', correlativo: 41, cliente_nombre: 'Cliente Boleta' },
};

function dispatchContext(document) {
  return {
    source_document: {
      id: document.id,
      type: document.tipo_comprobante,
      label: document.tipo_comprobante === '03' ? 'Boleta de venta' : 'Factura',
      number: `${document.serie}-${String(document.correlativo).padStart(8, '0')}`,
    },
    customer: {
      name: document.cliente_nombre,
      address: 'Av. Destino 200',
      ubigeo: '150103',
    },
    eligibility: {
      can_prepare: true,
      can_reserve: true,
      can_emit: true,
      reason: null,
      code: 'ELIGIBLE',
    },
    lines: [{
      id: document.id * 10,
      description: document.tipo_comprobante === '03' ? 'Producto de boleta' : 'Producto de factura',
      unit: 'NIU',
      invoiced: 100,
      cancelled: 0,
      reserved: 40,
      covered: 0,
      departure_confirmed: 0,
      available: 60,
      dispatchable: true,
      pending_adjustment: false,
      inventory_evidence_missing: false,
      requires_goods_confirmation: false,
    }],
  };
}

async function createGuideContext(browser, baseURL, contextOptions = {}) {
  const captured = { createPayload: null };
  const context = await browser.newContext({ baseURL, storageState: { cookies: [], origins: [] }, ...contextOptions });
  await context.addInitScript(() => localStorage.setItem('token', 'gre-e2e-token'));
  const page = await context.newPage();

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    let body = {};

    if (path === '/users/me') body = user;
    else if (path === '/tenant') body = tenant;
    else if (path === '/tenant/subscription-status') body = {};
    else if (path === '/sunat/exchange-rate') body = { buy: '3.50', sell: '3.51' };
    else if (path === '/facturas-emitidas/page') {
      const type = url.searchParams.get('tipo_comprobante');
      const items = Object.values(documents).filter((document) => document.tipo_comprobante === type);
      body = { items, total: items.length, skip: 0, limit: 15 };
    } else if (path.match(/^\/facturacion\/comprobantes\/\d+\/despacho-contexto$/)) {
      const id = Number(path.split('/')[3]);
      body = dispatchContext(documents[id]);
    } else if (path === '/guias-remision/desde-comprobante' && request.method() === 'POST') {
      captured.createPayload = request.postDataJSON();
      body = { id: 900, version: 1, guides: [{ id: 99, tipo_documento: '09' }] };
    } else if (path === '/guias-remision/99') {
      body = {
        id: 99,
        tipo_documento: '09',
        estado: 'borrador',
        serie: null,
        correlativo: null,
        fecha_emision: '2026-09-18T12:00:00-05:00',
        fecha_traslado: '2026-09-19T12:00:00-05:00',
        motivo_traslado: '01',
        modalidad_traslado: '02',
        peso_bruto_total: 5,
        unidad_medida_peso: 'KGM',
        partida_ubigeo: '150101',
        partida_direccion: 'Av. Origen 100',
        llegada_ubigeo: '150103',
        llegada_direccion: 'Av. Destino 200',
        items: [{ id: 1, descripcion: 'Producto de boleta', cantidad: 10, unidad_medida: 'NIU' }],
        actions: {},
      };
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });

  return { context, page, captured };
}

function inputAfterLabel(page, text) {
  return page.getByRole('group', { name: new RegExp(`^${text}(?:\\s*\\*)?$`, 'i') }).locator('input').first();
}

async function captureGuideUi(page, filename) {
  if (process.env.CAPTURE_GUIDE_UI !== '1') return;
  await mkdir('output/playwright', { recursive: true });
  await page.screenshot({ path: `output/playwright/${filename}`, fullPage: true });
  const main = page.locator('main');
  await main.evaluate((element) => element.scrollTo({ top: element.scrollHeight, behavior: 'instant' }));
  await page.screenshot({ path: `output/playwright/${filename.replace('.png', '-bottom.png')}` });
  await main.evaluate((element) => element.scrollTo({ top: 0, behavior: 'instant' }));
}

test.describe('GRE de venta desde factura y boleta', () => {
  test('la matriz privado, público y M1/L no solicita datos ficticios', async ({ browser, baseURL }) => {
    const { context, page } = await createGuideContext(browser, baseURL);
    try {
      await page.goto('/guias/nueva?comprobante_id=527');
      await expect(page.getByRole('heading', { level: 2, name: /Nueva guía remitente/i })).toBeVisible();
      await expect(page.getByText(/Factura F001-00000178/i)).toBeVisible();
      await expect(page.getByRole('cell', { name: '60' })).toBeVisible();
      await captureGuideUi(page, 'guia-nueva-desktop.png');

      await expect(inputAfterLabel(page, 'Placa')).toBeVisible();
      await expect(inputAfterLabel(page, 'Documento del conductor')).toBeVisible();

      await page.getByText('Vehículo M1/L', { exact: true }).click();
      await expect(inputAfterLabel(page, 'Placa')).toBeVisible();
      await expect(inputAfterLabel(page, 'Documento del conductor')).toHaveCount(0);

      await page.getByRole('button', { name: /Público Empresa transportista/i }).click();
      await expect(inputAfterLabel(page, 'RUC del transportista')).toBeVisible();
      await expect(inputAfterLabel(page, 'Documento del conductor')).toHaveCount(0);
      await expect(inputAfterLabel(page, 'Placa')).toHaveCount(0);
      await expect(page.getByText(/Se requerirá GRE transportista 31/i)).toBeVisible();

      await page.getByText('Vehículo M1/L', { exact: true }).click();
      await expect(inputAfterLabel(page, 'RUC del transportista')).toHaveCount(0);
      await expect(inputAfterLabel(page, 'Placa')).toBeVisible();
      await expect(inputAfterLabel(page, 'Documento del conductor')).toHaveCount(0);
    } finally {
      await context.close();
    }
  });

  test('guarda un despacho parcial desde boleta usando el endpoint neutral', async ({ browser, baseURL }) => {
    const { context, page, captured } = await createGuideContext(browser, baseURL);
    try {
      await page.goto('/guias/nueva?comprobante_id=528');
      await expect(page.getByText(/Boleta de venta B001-00000041/i)).toBeVisible();

      await page.locator('tbody input[type="number"]').fill('10');
      await inputAfterLabel(page, 'Peso bruto').fill('5');
      await inputAfterLabel(page, 'Ubigeo de partida').fill('150101');
      await inputAfterLabel(page, 'Dirección de partida').fill('Av. Origen 100');
      await inputAfterLabel(page, 'Placa').fill('ABC123');
      await inputAfterLabel(page, 'Documento del conductor').fill('72758912');
      await inputAfterLabel(page, 'Licencia').fill('Q12345678');
      await inputAfterLabel(page, 'Nombres').fill('Ana');
      await inputAfterLabel(page, 'Apellidos').fill('Rojas');

      await page.getByRole('button', { name: /Guardar borrador/i }).click();
      await expect(page).toHaveURL(/\/guias\/99$/);
      expect(captured.createPayload.fiscal_document_id).toBe(528);
      expect(captured.createPayload.lines).toEqual([{
        fiscal_document_item_id: 5280,
        quantity: 10,
        confirmed_as_goods: true,
      }]);
      expect(captured.createPayload.modalidad_traslado).toBe('02');
      expect(captured.createPayload.vehiculo_placa).toBe('ABC123');
      expect(captured.createPayload.conductor_nro_doc).toBe('72758912');
    } finally {
      await context.close();
    }
  });

  test('mantiene el formulario legible y sin desborde horizontal en móvil', async ({ browser, baseURL }) => {
    const { context, page } = await createGuideContext(browser, baseURL, {
      viewport: { width: 390, height: 844 },
    });
    try {
      await page.goto('/guias/nueva?comprobante_id=527');
      await expect(page.getByRole('heading', { level: 2, name: /Nueva guía remitente/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /Guardar borrador/i })).toBeVisible();
      await captureGuideUi(page, 'guia-nueva-mobile.png');
      const dimensions = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        content: document.documentElement.scrollWidth,
      }));
      expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1);
    } finally {
      await context.close();
    }
  });
});
