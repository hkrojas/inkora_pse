import { test, expect } from '@playwright/test';

const API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000';
const user = {
  id: 91, email: 'notes.qa@inkora.test', nombre_completo: 'Notes QA',
  rol: 'admin', is_superadmin: false, tenant_id: 9, must_change_password: false,
};
const document = {
  id: 44, document_number: 'F001-000044', serie: 'F001', correlativo: 44,
  estado: 'facturada', sunat_accepted: true, total_venta: 118,
  moneda: 'PEN', cliente: { razon_social: 'Cliente de prueba SAC' },
};
const noteContext = {
  document: { ...document, number: document.document_number, total: 118 },
  lines: [{
    id: 501, descripcion: 'Impresion de catalogos', cantidad: 2,
    precio_unitario: 59, total: 118, cantidad_devolvible: 2,
    tipo_afectacion_igv: '10',
  }],
  balance: {
    original: 118, creditos_aceptados: 0, debitos_aceptados: 0,
    ajustes_reservados: 0, maximo_disponible: 118,
    saldo_fiscal: 118, pagos: 0, saldo_por_cobrar: 118,
  },
  allowed_motives: {
    credito: { '01': 'Anulacion de la operacion', '04': 'Descuento global', '07': 'Devolucion por item', '13': 'Correccion del monto pendiente' },
    debito: { '01': 'Intereses por mora', '03': 'Otros conceptos', '13': 'Penalidades (inafectas)' },
  },
  warehouses: [{ id: 3, name: 'Almacen principal', is_default: true }],
};

async function openMockedNotes(browser, baseURL, viewport) {
  const context = await browser.newContext({ baseURL, viewport, storageState: { cookies: [], origins: [] } });
  await context.addInitScript(() => localStorage.setItem('token', 'notes-v2-visual-token'));
  const page = await context.newPage();
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/\/$/, '');
    let payload = {};
    if (path === '/users/me') payload = user;
    else if (path === '/tenant') payload = { id: 9, business_name: 'Inkora QA', business_ruc: '20123456789', is_active: true };
    else if (path === '/tenant/subscription-status') payload = {};
    else if (path === '/sunat/exchange-rate') payload = { buy: '3.70', sell: '3.72' };
    else if (path === '/facturas-emitidas/page') payload = { items: [document], total: 1 };
    else if (path === '/notas/contexto/44') payload = noteContext;
    else if (path === '/notas' && route.request().method() === 'POST') payload = { id: 71, estado: 'borrador', total_venta: 20, message: 'Borrador guardado' };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
  });
  await page.goto('/notas/nueva');
  return { context, page };
}

test.describe('Notas fiscales v2', () => {
  test('descuento global exige importe explicito y guarda borrador', async ({ browser, baseURL }) => {
    const { context, page } = await openMockedNotes(browser, baseURL, { width: 1440, height: 900 });
    try {
      await expect(page.getByRole('heading', { name: /nueva nota/i })).toBeVisible();
      await page.getByLabel('Seleccionar comprobante').selectOption('44');
      await page.getByLabel('Motivo', { exact: true }).selectOption('04');
      await page.getByLabel('Sustento del ajuste').fill('Descuento comercial acordado con el cliente');
      await page.getByLabel('Importe').fill('20');
      await expect(page.getByText('S/ 20.00').first()).toBeVisible();
      await expect(page.getByRole('button', { name: /emitir a sunat/i })).toBeEnabled();
      await page.getByRole('button', { name: /guardar borrador/i }).click();
      await expect(page.getByText('Borrador guardado').first()).toBeVisible();
    } finally {
      await context.close();
    }
  });

  for (const width of [360, 768]) {
    test(`sin desbordamiento horizontal a ${width}px y CTA bloqueado`, async ({ browser, baseURL }) => {
      const { context, page } = await openMockedNotes(browser, baseURL, { width, height: 820 });
      try {
        await expect(page.getByRole('button', { name: /^emitir$/i })).toBeDisabled();
        const overflows = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
        expect(overflows).toBe(false);
      } finally {
        await context.close();
      }
    });
  }
});
