import { expect, test } from '@playwright/test';
import { attachApiOriginGuard, attachCriticalErrorCollector } from './helpers/assertions';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const source = { id: 1, name: 'Depósito de papel', sunat_code: '0001', address: 'Dirección de prueba', ubigeo: '150101' };
const destination = { ...source, id: 2, name: 'Tienda principal', sunat_code: '0000' };
const line = (id, description, pending, stock, controlled = true) => ({
  id, product_id: controlled ? id : null, description, product_code: `QA-${id}`, unit_code: 'NIU',
  inventory_controlled: controlled, quantity: pending, pending_assignment: pending, available_stock: stock,
  cancelled: 0, assigned: 0, departed: 0, in_transit: 0, received: 0,
});
const mixedLines = () => [
  line(1, 'Papel sin existencias', 40000, 0),
  line(2, 'Cartulina disponible', 20, 8.5),
  line(3, 'Bien manual', 12, null, false),
  line(4, 'Sobres', 5, 50),
  line(5, 'Stock sin consultar', 10, null),
];

async function openTransfer(browser, baseURL, { width = 1440, theme = 'light', lines = mixedLines(), dispatches = [], requiresGre = true, rejectReservation = false } = {}) {
  const context = await browser.newContext({ baseURL, viewport: { width, height: 960 }, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
  await context.addInitScript((value) => {
    localStorage.setItem('token', 'internal-transfer-guards-qa');
    localStorage.setItem('inkora-theme', value);
  }, theme);
  const page = await context.newPage();
  const data = { id: 1, version: 1, status: 'pending', reason: 'Reposición de prueba', source_establishment: source, destination_establishment: destination, requires_gre: requiresGre, lines, dispatches };
  const writes = [];
  const unexpected = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(/\/$/, '');
    let payload;
    if (request.method() === 'GET') {
      if (path === '/users/me') payload = { id: 73, tenant_id: 73, rol: 'admin', nombre_completo: 'Pruebas QA', email: 'guards@inkora.test', is_superadmin: false, must_change_password: false };
      else if (path === '/tenant/subscription-status') payload = { fiscal_feature_flags: { internal_transfers: true } };
      else if (path === '/sunat/exchange-rate') payload = { buy: 3.7, sell: 3.72 };
      else if (path === '/tenant') payload = { id: 73, business_name: 'Pruebas QA', is_active: true };
      else if (path === '/traslados-internos/1') payload = data;
    } else if (request.method() === 'POST' && path === '/traslados-internos/1/despachos') {
      const body = request.postDataJSON();
      writes.push({ path, body });
      if (rejectReservation) {
        await route.fulfill({ status: 409, json: { detail: { message: 'El stock disponible cambió. Revisa la cantidad.' } } });
        return;
      }
      for (const selected of body.lines) {
        const item = data.lines.find((row) => row.id === selected.transfer_line_id);
        item.assigned += selected.quantity;
        item.pending_assignment -= selected.quantity;
        if (item.inventory_controlled) item.available_stock -= selected.quantity;
      }
      data.dispatches.push({ id: 80, status: 'reserved', guide: null, lines: body.lines.map((item, index) => ({ id: index + 1, ...item, departed_quantity: 0, received_quantity: 0 })) });
      payload = { id: 80 };
    } else if (request.method() === 'POST' && path === '/traslados-internos/despachos/10/confirmar-salida') {
      writes.push({ path, body: request.postDataJSON() });
      data.dispatches[0].departure_confirmed_at = '2026-10-17T12:00:00Z';
      data.dispatches[0].lines[0].departed_quantity = 5;
      payload = data.dispatches[0];
    }
    if (payload === undefined) unexpected.push(`${request.method()} ${path}`);
    await route.fulfill({ status: payload === undefined ? 500 : 200, json: payload ?? { detail: 'Solicitud no prevista' } });
  });
  const errors = attachCriticalErrorCollector(page);
  const origin = attachApiOriginGuard(page);
  await page.goto('/traslados-internos/1');
  await expect(page.locator('.internal-transfer-page').getByRole('heading', { name: 'Traslado TI-1', exact: true })).toBeVisible();
  return { context, page, writes, unexpected, errors, origin };
}

for (const [width, theme] of [[1440, 'light'], [390, 'dark']]) {
  test(`reserva parcial, límites y bienes manuales a ${width}px ${theme}`, async ({ browser, baseURL }, testInfo) => {
    const { context, page, writes, unexpected, errors, origin } = await openTransfer(browser, baseURL, { width, theme });
    try {
      await page.getByRole('button', { name: 'Preparar viaje', exact: true }).click();
      const drawer = page.getByRole('dialog', { name: 'Preparar viaje', exact: true });
      const reserve = drawer.getByRole('button', { name: 'Reservar para este viaje', exact: true });
      const fields = ['Papel sin existencias', 'Cartulina disponible', 'Bien manual', 'Sobres', 'Stock sin consultar'].map((name) => drawer.getByRole('spinbutton', { name: `Cantidad para ${name}`, exact: true }));
      for (const [index, value] of ['0', '8.5', '12', '5', '0'].entries()) await expect(fields[index]).toHaveValue(value);
      await expect(drawer.getByText('Sin stock disponible. Puedes preparar los demás bienes.', { exact: true })).toBeVisible();
      await expect(drawer.getByText('Bien sin control de stock.', { exact: true })).toBeVisible();
      await expect(reserve).toBeEnabled();
      for (const [field, value, message] of [
        [fields[0], '1', 'La cantidad supera el stock disponible en origen.'],
        [fields[1], '8.5001', 'La cantidad supera el stock disponible en origen.'],
        [fields[1], '21', 'La cantidad supera lo pendiente de preparar.'],
        [fields[1], '-1', 'Ingresa una cantidad de cero o más.'],
        [fields[1], '0.00001', 'Usa como máximo cuatro decimales.'],
        [fields[2], '13', 'La cantidad supera lo pendiente de preparar.'],
        [fields[4], '1', 'La cantidad supera el stock disponible en origen.'],
      ]) {
        const previous = await field.inputValue();
        await field.fill(value);
        await expect(field).toHaveAttribute('aria-invalid', 'true');
        await expect(drawer.getByRole('alert')).toHaveText(message);
        await expect(reserve).toBeDisabled();
        expect(writes).toEqual([]);
        await field.fill(previous);
      }
      await drawer.getByRole('heading', { name: 'Preparar viaje', exact: true }).click();
      await drawer.locator('.ink-drawer-body').evaluate((body) => { body.scrollTop = 0; });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`preparar-viaje-${width}.png`), animations: 'disabled' });
      for (const field of fields) await field.fill('0');
      await expect(reserve).toBeDisabled();
      await fields[1].fill('7.25');
      await reserve.click();
      await expect(drawer).toBeHidden();
      expect(writes).toHaveLength(1);
      expect(writes[0].body.lines).toEqual([{ transfer_line_id: 2, quantity: 7.25 }]);
      expect(writes[0].body.idempotency_key).toMatch(/^[\da-f-]{36}$/);
      await page.getByRole('button', { name: 'Preparar viaje', exact: true }).click();
      await expect(fields[1]).toHaveValue('1.25');
      await expect(fields[2]).toHaveValue('12');
      await drawer.getByRole('button', { name: 'Volver', exact: true }).click();
      await expect(drawer).toBeHidden();
      expect(writes).toHaveLength(1);
      expect(unexpected).toEqual([]);
      errors.assertClean();
      origin.assertClean();
    } finally { await context.close(); }
  });
}

test('stock cero, negativo o desconocido no permite reservar; el bien manual sí', async ({ browser, baseURL }) => {
  const { context, page, writes, unexpected, errors } = await openTransfer(browser, baseURL, { lines: [line(1, 'Sin stock', 40, 0), line(2, 'Saldo negativo', 40, -2), line(3, 'Sin consulta', 40, null)] });
  try {
    await page.getByRole('button', { name: 'Preparar viaje', exact: true }).click();
    const drawer = page.getByRole('dialog', { name: 'Preparar viaje', exact: true });
    await expect(drawer.getByRole('button', { name: 'Reservar para este viaje' })).toBeDisabled();
    for (const field of await drawer.getByRole('spinbutton').all()) await expect(field).toHaveValue('0');
    await drawer.getByRole('button', { name: 'Volver', exact: true }).click();
    expect(writes).toEqual([]);
    expect(unexpected).toEqual([]);
    errors.assertClean();
  } finally { await context.close(); }
  const manual = await openTransfer(browser, baseURL, { lines: [line(1, 'Bien manual', 2.5, null, false)] });
  try {
    await manual.page.getByRole('button', { name: 'Preparar viaje', exact: true }).click();
    await manual.page.getByRole('button', { name: 'Reservar para este viaje' }).click();
    await expect(manual.page.getByRole('dialog', { name: 'Preparar viaje', exact: true })).toBeHidden();
    expect(manual.writes[0].body.lines).toEqual([{ transfer_line_id: 1, quantity: 2.5 }]);
    expect(manual.unexpected).toEqual([]);
    manual.errors.assertClean();
  } finally { await manual.context.close(); }
});

test('el rechazo del servidor conserva la cantidad y no informa una reserva exitosa', async ({ browser, baseURL }) => {
  const { context, page, writes, unexpected, errors, origin } = await openTransfer(browser, baseURL, { rejectReservation: true, lines: [line(1, 'Cartulina', 10, 10)] });
  try {
    await page.getByRole('button', { name: 'Preparar viaje', exact: true }).click();
    const drawer = page.getByRole('dialog', { name: 'Preparar viaje', exact: true });
    const field = drawer.getByRole('spinbutton');
    await field.fill('2.5');
    await drawer.getByRole('button', { name: 'Reservar para este viaje' }).click();
    await expect(page.getByText('El stock disponible cambió. Revisa la cantidad.', { exact: true })).toBeVisible();
    await expect(drawer).toBeVisible();
    await expect(field).toHaveValue('2.5');
    await expect(drawer.getByRole('button', { name: 'Reservar para este viaje' })).toBeEnabled();
    expect(writes).toHaveLength(1);
    expect(unexpected).toEqual([]);
    expect(errors.errors.filter((error) => !error.includes('409'))).toEqual([]);
    origin.assertClean();
  } finally { await context.close(); }
});

for (const [width, theme] of [[1440, 'light'], [390, 'dark']]) {
  test(`salida física exige confirmar y respeta guía aceptada a ${width}px ${theme}`, async ({ browser, baseURL }, testInfo) => {
    const dispatch = (id, status) => ({ id, status: 'reserved', departure_confirmed_at: null, guide: { id, number: `T001-${id}`, status }, lines: [{ id, transfer_line_id: 1, quantity: 5, departed_quantity: 0, received_quantity: 0 }] });
    const { context, page, writes, unexpected, errors, origin } = await openTransfer(browser, baseURL, { width, theme, dispatches: [dispatch(10, 'aceptada'), dispatch(11, 'rechazada'), { ...dispatch(12, 'aceptada'), departure_confirmed_at: '2026-10-16T12:00:00Z' }] });
    try {
      const cards = page.locator('.internal-transfer-dispatch-card');
      const departure = cards.first().getByRole('button', { name: 'Confirmar salida física', exact: true });
      await expect(cards.nth(1).getByRole('button', { name: 'Confirmar salida física', exact: true })).toBeDisabled();
      await expect(cards.nth(2).getByRole('button', { name: 'Confirmar salida física', exact: true })).toBeDisabled();
      await expect(cards.first().getByRole('button', { name: 'Registrar recepción' })).toBeDisabled();
      await departure.click();
      const dialog = page.getByRole('dialog', { name: 'Confirmar salida física', exact: true });
      await expect(dialog).toContainText(`Viaje 1 · ${source.name} → ${destination.name}`);
      await expect(dialog).toContainText('Se descontarán las existencias del origen');
      expect(writes).toEqual([]);
      await page.screenshot({ path: testInfo.outputPath(`confirmar-salida-${width}.png`), animations: 'disabled' });
      await dialog.getByRole('button', { name: 'Todavía no', exact: true }).click();
      await expect(dialog).toBeHidden();
      expect(writes).toEqual([]);
      await departure.click();
      await dialog.press('Escape');
      await expect(dialog).toBeHidden();
      expect(writes).toEqual([]);
      await departure.click();
      await dialog.getByRole('button', { name: 'Sí, los bienes ya salieron', exact: true }).click();
      await expect(dialog).toBeHidden();
      await expect(departure).toBeDisabled();
      await expect(cards.first().getByRole('button', { name: 'Registrar recepción' })).toBeEnabled();
      expect(writes).toHaveLength(1);
      expect(writes[0].path).toBe('/traslados-internos/despachos/10/confirmar-salida');
      expect(writes[0].body.idempotency_key).toMatch(/^[\da-f-]{36}$/);
      expect(unexpected).toEqual([]);
      errors.assertClean();
      origin.assertClean();
    } finally { await context.close(); }
  });
}

test('el viaje documental sin GRE también confirma salida sin anunciar descuento de stock', async ({ browser, baseURL }) => {
  const dispatch = { id: 10, status: 'reserved', guide: null, lines: [{ id: 10, transfer_line_id: 1, quantity: 5, departed_quantity: 0, received_quantity: 0 }] };
  const { context, page, writes, unexpected, errors } = await openTransfer(browser, baseURL, { lines: [line(1, 'Bien manual', 5, null, false)], dispatches: [dispatch], requiresGre: false });
  try {
    await page.getByRole('button', { name: 'Confirmar salida física', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirmar salida física', exact: true });
    await expect(dialog).toContainText('Los bienes quedarán en tránsito.');
    await expect(dialog).not.toContainText('Se descontarán las existencias');
    expect(writes).toEqual([]);
    await dialog.getByRole('button', { name: 'Sí, los bienes ya salieron', exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByRole('button', { name: 'Confirmar salida física', exact: true })).toBeDisabled();
    expect(writes).toHaveLength(1);
    expect(unexpected).toEqual([]);
    errors.assertClean();
  } finally { await context.close(); }
});
