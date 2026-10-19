import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import AxeBuilder from '@axe-core/playwright';
import { chooseInkoraOption } from './helpers/inkora-controls';

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
  const captured = { createPayload: null, nextError: null, requests: 0, emissions: 0, keys: [] };
  const context = await browser.newContext({ baseURL, storageState: { cookies: [], origins: [] }, ...contextOptions });
  await context.addInitScript(() => localStorage.setItem('token', 'gre-e2e-token'));
  const page = await context.newPage();

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    let body = {};

    if (request.method() === 'POST' && ['/guias-remision/desde-comprobante', '/guias-remision/transportista'].includes(path)) {
      captured.requests += 1;
      captured.keys.push(request.postDataJSON().idempotency_key);
      if (captured.nextError) {
        const error = captured.nextError;
        captured.nextError = null;
        return route.fulfill({ status: error.status, contentType: 'application/json', body: JSON.stringify({ detail: error.detail }) });
      }
    }

    if (path === '/guias-remision/99/emitir') { captured.emissions += 1; body = { job_id: 50, job_status: 'pending' }; }
    else if (path === '/users/me') body = user;
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
  return page.getByLabel(text, { exact: true }).and(page.locator('input')).first();
}

async function goTransport(page) {
  const quantity = page.locator('tbody input[type="number"]').first();
  if (!(await page.getByRole('heading', { name: /Paso 2 de 3/ }).isVisible())) {
    await expect(quantity).toBeVisible();
    await quantity.fill('10');
    await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  }
  await expect(page.getByRole('heading', { name: /Paso 2 de 3/ })).toBeVisible();
}

async function goReview(page) {
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Paso 3 de 3/ })).toBeVisible();
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

      await goTransport(page);
      await expect(inputAfterLabel(page, 'Placa')).toBeVisible();
      await expect(inputAfterLabel(page, 'Documento del conductor')).toBeVisible();

      await page.getByText('Opciones del vehículo', { exact: true }).click();
      await page.getByText('Vehículo M1/L', { exact: true }).click();
      await expect(inputAfterLabel(page, 'Placa')).toBeVisible();
      await expect(inputAfterLabel(page, 'Documento del conductor')).toHaveCount(0);

      await goTransport(page);
    await page.getByRole('button', { name: /Empresa de transporte Contratamos/i }).click();
      await expect(inputAfterLabel(page, 'RUC del transportista')).toBeVisible();
      await expect(inputAfterLabel(page, 'Documento del conductor')).toHaveCount(0);
      await expect(inputAfterLabel(page, 'Placa')).toHaveCount(0);
      await expect(page.getByText(/Necesitarás la guía de la empresa transportista/i)).toBeVisible();

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
      await goTransport(page);
      await inputAfterLabel(page, 'Peso bruto').fill('5');
      await inputAfterLabel(page, 'Ubigeo de partida').fill('150101');
      await inputAfterLabel(page, 'Dirección de partida').fill('Av. Origen 100');
      await inputAfterLabel(page, 'Placa').fill('ABC123');
      await inputAfterLabel(page, 'Documento del conductor').fill('72758912');
      await inputAfterLabel(page, 'Licencia').fill('Q12345678');
      await inputAfterLabel(page, 'Nombres').fill('Ana');
      await inputAfterLabel(page, 'Apellidos').fill('Rojas');

      await goReview(page);
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
      await expect(page.getByRole('button', { name: 'Continuar', exact: true })).toBeVisible();
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

async function assertPlaceholderContrast(input) {
  const ratio = await input.evaluate((element) => {
    const rgb = (value) => value.match(/[\d.]+/g).slice(0, 3).map(Number);
    const luminance = (color) => rgb(color).map((part) => part / 255).map((part) => part <= 0.04045 ? part / 12.92 : ((part + 0.055) / 1.055) ** 2.4).reduce((sum, part, index) => sum + part * [0.2126, 0.7152, 0.0722][index], 0);
    const foreground = luminance(getComputedStyle(element, '::placeholder').color);
    const background = luminance(getComputedStyle(element).backgroundColor);
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
  });
  expect(ratio).toBeGreaterThanOrEqual(4.5);
}

async function fillSaleGuide(page) {
  await goTransport(page);
  const fields = { 'Peso bruto': '5', 'Ubigeo de partida': '150101', 'Dirección de partida': 'Av. Origen 100', 'Placa': 'ABC123', 'Documento del conductor': '72758912', 'Licencia': 'Q12345678', 'Nombres': 'Ana', 'Apellidos': 'Rojas' };
  for (const [label, value] of Object.entries(fields)) await inputAfterLabel(page, label).fill(value);
}

async function fillCarrierGuide(page) {
  const values = { 'RUC emisor GRE 09': '20123456789', 'Número GRE 09': '1', 'RUC emisor factura de bienes': '20123456789', 'Número factura': '1', 'RUC remitente': '20123456789', 'Razón social remitente': 'Remitente demo', 'RUC destinatario': '20987654321', 'Razón social destinatario': 'Destino demo', 'Peso total (kg)': '5', 'Ubigeo partida': '150101', 'Dirección partida': 'Av. Origen 100', 'Ubigeo llegada': '150103', 'Dirección llegada': 'Av. Destino 200', 'Placa': 'ABC123', 'DNI del conductor': '72758912', 'Nombres': 'Ana', 'Apellidos': 'Rojas', 'Licencia': 'Q12345678', 'Descripción del bien 1': 'Bien de prueba' };
  for (const [label, value] of Object.entries(values)) await page.getByLabel(label, { exact: true }).and(page.locator('input')).fill(value);
}

for (const [width, theme] of [[1440, 'light'], [390, 'dark']]) {
  for (const carrier of [false, true]) {
    test(`campos accesibles y errores recuperables ${carrier ? 'transportista' : 'remitente'} ${width}px ${theme}`, async ({ browser, baseURL }, testInfo) => {
      const { context, page, captured } = await createGuideContext(browser, baseURL, { viewport: { width, height: 900 }, colorScheme: theme });
      try {
        await page.goto(carrier ? '/guias/nueva-transportista' : '/guias/nueva?comprobante_id=527');
        if (!carrier) await goTransport(page);
        const save = page.getByRole('button', { name: carrier ? 'Guardar borrador 31' : 'Continuar', exact: true });
        await expect(save).toBeVisible();
        const name = carrier ? 'DNI del conductor' : 'Documento del conductor';
        const driver = carrier ? page.getByLabel(name, { exact: true }).and(page.locator('input')) : inputAfterLabel(page, name);
        await expect(driver).toBeVisible();
        await assertPlaceholderContrast(carrier ? page.getByLabel('Licencia', { exact: true }).and(page.locator('input')) : inputAfterLabel(page, 'Licencia'));
        if (carrier) {
          await page.getByText('DNI del conductor', { exact: true }).click();
          await expect(driver).toBeFocused();
          await driver.press('Tab');
          await expect(page.getByLabel('Nombres', { exact: true }).and(page.locator('input'))).toBeFocused();
        }
        const analysis = await new AxeBuilder({ page }).include('.guide-accessible-form').analyze();
        expect(analysis.violations.filter((issue) => ['critical', 'serious'].includes(issue.impact))).toEqual([]);

        await save.click();
        const summary = page.getByRole('alert').filter({ hasText: 'Revisa la guía' });
        await expect(summary).toBeFocused();
        expect(captured.requests).toBe(0);
        await expect(driver).toHaveAttribute('aria-invalid', 'true');
        await summary.getByRole('button', { name: new RegExp(`^${name}:`) }).click();
        await expect(driver).toBeFocused();
        if (carrier) await fillCarrierGuide(page); else await fillSaleGuide(page);
        await expect(driver).toHaveAttribute('aria-invalid', 'false');

        if (!carrier) await goReview(page);
        const finalSave = page.getByRole('button', { name: carrier ? 'Guardar borrador 31' : 'Guardar borrador', exact: true });
        captured.nextError = { status: 422, detail: [{ loc: ['body', 'conductor_licencia'], msg: 'Invalid value', type: 'value_error' }] };
        await finalSave.click();
        await expect(summary).toBeFocused();
        const license = carrier ? page.getByLabel('Licencia', { exact: true }).and(page.locator('input')) : inputAfterLabel(page, 'Licencia');
        await expect(license).toHaveAttribute('aria-invalid', 'true');
        await expect(license).toHaveAccessibleDescription(/Revisa este dato/);
        await expect(driver).toHaveValue('72758912');
        await summary.getByRole('button', { name: /^Licencia:/ }).click();
        await expect(license).toBeFocused();
        await page.screenshot({ path: testInfo.outputPath(`error-campo-${carrier ? 'transportista' : 'remitente'}-${width}.png`), fullPage: true });
        await license.fill('Q87654321');
        await expect(license).toHaveAttribute('aria-invalid', 'false');
        if (!carrier) await goReview(page);
        captured.nextError = { status: 503, detail: 'No se pudo conectar. Inténtalo nuevamente.' };
        await finalSave.click();
        await expect(summary).toBeFocused();
        await expect(summary).toContainText('No se pudo conectar');
        await expect(license).toHaveValue('Q87654321');
        expect(captured.requests).toBe(2);
        const errorAnalysis = await new AxeBuilder({ page }).include('.guide-accessible-form').analyze();
        expect(errorAnalysis.violations.filter((issue) => ['critical', 'serious'].includes(issue.impact))).toEqual([]);
        if (!carrier) await page.getByRole('button', { name: 'Atrás', exact: true }).click();
        await driver.click();
        await page.screenshot({ path: testInfo.outputPath(`campos-${carrier ? 'transportista' : 'remitente'}-${width}.png`), fullPage: true });
        await (carrier ? page.getByRole('spinbutton', { name: 'Cantidad del bien 1', exact: true }) : page.getByRole('textbox', { name: 'Observaciones', exact: true })).click();
        const bottomAnalysis = await new AxeBuilder({ page }).include('.guide-accessible-form').analyze();
        expect(bottomAnalysis.violations.filter((issue) => ['critical', 'serious'].includes(issue.impact))).toEqual([]);
        const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, content: document.documentElement.scrollWidth, mainWidth: document.querySelector('main').clientWidth, mainContent: document.querySelector('main').scrollWidth }));
        expect(dimensions.content).toBeLessThanOrEqual(dimensions.width + 1);
        expect(dimensions.mainContent).toBeLessThanOrEqual(dimensions.mainWidth + 1);
        if (carrier && width === 390) expect((await driver.boundingBox()).x).toBeGreaterThanOrEqual(16);
      } finally { await context.close(); }
    });
  }
}

test('el acuerdo de transporte sigue siendo obligatorio y los errores de cantidad llegan a su línea', async ({ browser, baseURL }) => {
  const { context, page, captured } = await createGuideContext(browser, baseURL);
  try {
    await page.goto('/guias/nueva?comprobante_id=527');
    await goTransport(page);
    await page.getByRole('button', { name: /Empresa de transporte Contratamos/i }).click();
    await page.getByRole('checkbox', { name: /^Registrar vehículo y conductor del transportista/ }).check();
    await fillSaleGuide(page);
    for (const [label, value] of Object.entries({ 'RUC del transportista': '20123456789', 'Razón social': 'Transportista demo', 'Registro MTC': 'MTC1234', 'Número de circulación': 'T123456' })) await inputAfterLabel(page, label).fill(value);
    const agreement = page.getByRole('checkbox', { name: /^Acuerdo confirmado/ });
    const save = page.getByRole('button', { name: 'Continuar', exact: true });
    await save.click();
    await expect(agreement).toHaveAttribute('aria-invalid', 'true');
    expect(captured.requests).toBe(0);
    await agreement.check();
    await expect(agreement).toHaveAttribute('aria-invalid', 'false');
    captured.nextError = { status: 422, detail: { errors: [{ field: 'lines.0.quantity', message: 'Esta cantidad supera el saldo disponible.' }] } };
    await goReview(page);
    await page.getByRole('button', { name: 'Guardar borrador', exact: true }).click();
    const quantity = page.locator('input[name="lines.5270.quantity"]');
    await expect(quantity).toHaveAttribute('aria-invalid', 'true');
    await expect(quantity).toHaveAccessibleDescription('Esta cantidad supera el saldo disponible.');
    expect(captured.requests).toBe(1);
    await page.getByRole('alert').filter({ hasText: 'Revisa la guía' }).getByRole('button', { name: /Cantidad de Producto de factura/ }).click();
    await quantity.fill('5');
    await expect(quantity).toHaveAttribute('aria-invalid', 'false');
  } finally { await context.close(); }
});

test('una conexión interrumpida no afirma que el borrador no existe', async ({ browser, baseURL }) => {
  const { context, page, captured } = await createGuideContext(browser, baseURL);
  try {
    await page.goto('/guias/nueva?comprobante_id=527');
    await fillSaleGuide(page);
    await goReview(page);
    await page.route(`${API_ORIGIN}/guias-remision/desde-comprobante`, (route) => route.abort('failed'));
    await page.getByRole('button', { name: 'Guardar borrador', exact: true }).click();
    const summary = page.getByRole('alert').filter({ hasText: 'Revisa la guía' });
    await expect(summary).toBeFocused();
    await expect(summary).toContainText('Revisa la bandeja de guías antes de volver a guardar');
    await expect(inputAfterLabel(page, 'Documento del conductor')).toHaveValue('72758912');
    expect(captured.requests).toBe(0);
  } finally { await context.close(); }
});

for (const width of [1440, 390]) {
  test(`tres pasos, consultas y emisión explícita ${width}px`, async ({ browser, baseURL }, testInfo) => {
    const { context, page, captured } = await createGuideContext(browser, baseURL, { viewport: { width, height: 1000 } });
    try {
      await page.goto('/guias/nueva?comprobante_id=527');
      await expect(page.getByRole('heading', { name: /Paso 1 de 3/ })).toBeVisible();
      await page.getByRole('button', { name: 'Continuar', exact: true }).click();
      await expect(page.getByRole('alert').filter({ hasText: /Revisa la guía/ })).toContainText('al menos un producto');
      expect(captured.requests).toBe(0);
      await goTransport(page);
      await expect(page.getByRole('button', { name: 'Consultar DNI', exact: true })).toBeDisabled();
      await page.route(`${API_ORIGIN}/consultar-documento/72758912`, (route) => route.fulfill({ json: { documento: '72758912', nombres: 'ANA', apellido_paterno: 'ROJAS', apellido_materno: 'DEMO' } }));
      await page.route(`${API_ORIGIN}/guias-remision/consultas/licencia/72758912`, (route) => route.fulfill({ json: { documento: '72758912', numero: 'Q72758912', categoria: 'A II', estado: 'VIGENTE', fecha_vencimiento: '2030-01-01' } }));
      await page.route(`${API_ORIGIN}/guias-remision/consultas/placa/ABC123`, (route) => route.fulfill({ json: { placa: 'ABC123', marca: 'DEMO', modelo: 'CARGA', color: 'BLANCO' } }));
      await inputAfterLabel(page, 'Documento del conductor').fill('72758912');
      await page.getByRole('button', { name: 'Consultar DNI', exact: true }).click();
      await expect(inputAfterLabel(page, 'Nombres')).toHaveValue('ANA');
      await page.getByRole('button', { name: 'Consultar licencia', exact: true }).click();
      await expect(inputAfterLabel(page, 'Licencia')).toHaveValue('Q72758912');
      await expect(page.getByRole('status').filter({ hasText: 'VIGENTE' })).toContainText('2030-01-01');
      await inputAfterLabel(page, 'Placa').fill('abc-123');
      await page.getByRole('button', { name: 'Consultar placa', exact: true }).click();
      await expect(page.getByRole('status').filter({ hasText: 'DEMO' })).toContainText('CARGA');
      await inputAfterLabel(page, 'Peso bruto').fill('5');
      await inputAfterLabel(page, 'Ubigeo de partida').fill('150101');
      await inputAfterLabel(page, 'Dirección de partida').fill('Av. Origen 100');
      await page.screenshot({ path: testInfo.outputPath(`asistente-consultas-${width}.png`), fullPage: true });
      const axe = await new AxeBuilder({ page }).include('.guide-accessible-form').analyze();
      expect(axe.violations.filter((issue) => ['critical', 'serious'].includes(issue.impact))).toEqual([]);
      await goReview(page);
      await expect(page.getByRole('region', { name: 'Resumen de la guía' })).toContainText('ANA ROJAS DEMO');
      await expect(page.getByRole('region', { name: 'Resumen de la guía' })).toContainText('10 NIU');
      expect(captured.requests).toBe(0);
      await page.screenshot({ path: testInfo.outputPath(`asistente-revision-${width}.png`), fullPage: true });
      await page.getByRole('button', { name: 'Emitir guía', exact: true }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      expect(captured.requests).toBe(0);
      await page.getByRole('dialog').getByRole('button', { name: 'Emitir guía', exact: true }).click();
      await expect(page).toHaveURL(/\/guias\/99$/);
      expect(captured.requests).toBe(1);
      expect(captured.emissions).toBe(1);
      expect(captured.createPayload.lines[0].quantity).toBe(10);
    } finally { await context.close(); }
  });
}

test('consultas tardías y fallidas conservan identidad y datos manuales', async ({ browser, baseURL }) => {
  const { context, page } = await createGuideContext(browser, baseURL);
  try {
    await page.goto('/guias/nueva?comprobante_id=527');
    await goTransport(page);
    let release;
    const delayed = new Promise((resolve) => { release = resolve; });
    let started;
    const requested = new Promise((resolve) => { started = resolve; });
    await page.route(`${API_ORIGIN}/consultar-documento/72758912`, async (route) => {
      started(); await delayed;
      await route.fulfill({ json: { documento: '72758912', nombres: 'PROVEEDOR', apellido_paterno: 'ROJAS' } });
    });
    await inputAfterLabel(page, 'Documento del conductor').fill('72758912');
    await page.getByRole('button', { name: 'Consultar DNI', exact: true }).click();
    await requested;
    await inputAfterLabel(page, 'Nombres').fill('Manual');
    release();
    await expect(page.getByRole('status').filter({ hasText: 'Conservamos tus cambios' })).toBeVisible();
    await expect(inputAfterLabel(page, 'Nombres')).toHaveValue('Manual');
    await page.route(`${API_ORIGIN}/guias-remision/consultas/licencia/72758912`, (route) => route.fulfill({ status: 503, json: { detail: 'Consulta no disponible.' } }));
    await inputAfterLabel(page, 'Licencia').fill('QMANUAL');
    await page.getByRole('button', { name: 'Consultar licencia', exact: true }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Consulta no disponible' })).toBeVisible();
    await expect(inputAfterLabel(page, 'Licencia')).toHaveValue('QMANUAL');
    await page.getByRole('button', { name: /Empresa de transporte Contratamos/ }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Cambiar modalidad', exact: true }).click();
    await page.route(`${API_ORIGIN}/consultar-documento/20123456789`, (route) => route.fulfill({ json: { documento: '20123456789', razon_social: 'TRANSPORTE DEMO SAC' } }));
    await inputAfterLabel(page, 'RUC del transportista').fill('20123456789');
    await page.getByRole('button', { name: 'Consultar RUC', exact: true }).click();
    await expect(inputAfterLabel(page, 'Razón social')).toHaveValue('TRANSPORTE DEMO SAC');
    await expect(inputAfterLabel(page, 'Dirección de llegada')).toHaveValue('Av. Destino 200');
  } finally { await context.close(); }
});

test('reintentar el mismo guardado conserva la clave y un fallo de emisión abre el borrador existente', async ({ browser, baseURL }) => {
  const { context, page, captured } = await createGuideContext(browser, baseURL);
  try {
    await page.goto('/guias/nueva?comprobante_id=527');
    await fillSaleGuide(page);
    await goReview(page);
    captured.nextError = { status: 503, detail: 'Sin respuesta del servidor.' };
    await page.getByRole('button', { name: 'Guardar borrador', exact: true }).click();
    await expect(page.getByRole('alert').filter({ hasText: 'Revisa la guía' })).toContainText('Sin respuesta');
    await page.route(`${API_ORIGIN}/guias-remision/99/emitir?mode=async`, (route) => route.abort('failed'));
    await page.getByRole('button', { name: 'Emitir guía', exact: true }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Emitir guía', exact: true }).click();
    await expect(page).toHaveURL(/\/guias\/99$/);
    expect(captured.requests).toBe(2);
    expect(captured.keys[0]).toBe(captured.keys[1]);
    await expect(page.getByText(/La guía quedó guardada.*No recibimos confirmación/)).toBeVisible();
  } finally { await context.close(); }
});

test('GRE transportista consulta RUC, DNI, licencia y placa sin guardar', async ({ browser, baseURL }) => {
  const { context, page, captured } = await createGuideContext(browser, baseURL);
  try {
    await page.goto('/guias/nueva-transportista');
    await page.route(`${API_ORIGIN}/consultar-documento/20123456789`, (route) => route.fulfill({ json: { documento: '20123456789', razon_social: 'REMITENTE DEMO' } }));
    await inputAfterLabel(page, 'RUC remitente').fill('20123456789');
    await page.getByRole('button', { name: 'Consultar RUC', exact: true }).first().click();
    await expect(inputAfterLabel(page, 'Razón social remitente')).toHaveValue('REMITENTE DEMO');
    await page.route(`${API_ORIGIN}/consultar-documento/72758912`, (route) => route.fulfill({ json: { documento: '72758912', nombres: 'ANA', apellido_paterno: 'DEMO' } }));
    await inputAfterLabel(page, 'DNI del conductor').fill('72758912');
    await page.getByRole('button', { name: 'Consultar DNI', exact: true }).click();
    await expect(inputAfterLabel(page, 'Nombres')).toHaveValue('ANA');
    await page.route(`${API_ORIGIN}/guias-remision/consultas/licencia/72758912`, (route) => route.fulfill({ json: { documento: '72758912', numero: 'Q72758912' } }));
    await page.getByRole('button', { name: 'Consultar licencia', exact: true }).click();
    await expect(inputAfterLabel(page, 'Licencia')).toHaveValue('Q72758912');
    await page.route(`${API_ORIGIN}/guias-remision/consultas/placa/ABC123`, (route) => route.fulfill({ json: { placa: 'ABC123', marca: 'DEMO', modelo: 'CARGA' } }));
    await inputAfterLabel(page, 'Placa').fill('abc-123');
    await page.getByRole('button', { name: 'Consultar placa', exact: true }).click();
    await expect(inputAfterLabel(page, 'Placa')).toHaveValue('ABC123');
    await expect(page.getByRole('status').filter({ hasText: 'CARGA' })).toBeVisible();
    expect(captured.requests).toBe(0);
  } finally { await context.close(); }
});

test('cambiar DNI descarta su respuesta anterior y cambiar venta renueva el destino', async ({ browser, baseURL }) => {
  const { context, page } = await createGuideContext(browser, baseURL);
  try {
    await page.goto('/guias/nueva?comprobante_id=527');
    await goTransport(page);
    let release;
    const delayed = new Promise((resolve) => { release = resolve; });
    let started;
    const requested = new Promise((resolve) => { started = resolve; });
    await page.route(`${API_ORIGIN}/consultar-documento/72758912`, async (route) => {
      started(); await delayed;
      await route.fulfill({ json: { documento: '72758912', nombres: 'OLD', apellido_paterno: 'PERSON' } });
    });
    await inputAfterLabel(page, 'Documento del conductor').fill('72758912');
    await page.getByRole('button', { name: 'Consultar DNI', exact: true }).click();
    await requested;
    await inputAfterLabel(page, 'Documento del conductor').fill('87654321');
    release();
    await expect(inputAfterLabel(page, 'Nombres')).toHaveValue('');
    await inputAfterLabel(page, 'Dirección de llegada').fill('Dirección anterior editada');
    await page.getByRole('button', { name: 'Atrás', exact: true }).click();
    await page.route(`${API_ORIGIN}/facturacion/comprobantes/528/despacho-contexto`, (route) => route.fulfill({ json: { ...dispatchContext(documents[528]), customer: { name: 'Cliente Boleta', address: 'OTRA DIRECCIÓN', ubigeo: '150104' } } }));
    await chooseInkoraOption(page, 'Factura o boleta de origen', 'Boleta · B001-00000041 · Cliente Boleta');
    await expect(page.getByText(/Boleta de venta B001-00000041/)).toBeVisible();
    await goTransport(page);
    await expect(inputAfterLabel(page, 'Dirección de llegada')).toHaveValue('OTRA DIRECCIÓN');
    await expect(inputAfterLabel(page, 'Ubigeo de llegada')).toHaveValue('150104');
  } finally { await context.close(); }
});
