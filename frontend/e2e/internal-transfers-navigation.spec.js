import { expect, test } from '@playwright/test';
import { attachApiOriginGuard, attachCriticalErrorCollector } from './helpers/assertions';

const API_ORIGIN = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const emptyPage = { items: [], total: 0, skip: 0, limit: 15, counts: {} };
const source = { id: 1, name: 'Depósito de papel', sunat_code: '0001', address: 'Dirección de prueba', ubigeo: '150101', is_active: true };
const destination = { ...source, id: 2, name: 'Tienda principal', sunat_code: '0000' };
const transfers = Array.from({ length: 16 }, (_, index) => ({
  id: index + 1, status: index % 3 === 0 ? 'draft' : 'pending', created_at: '2026-10-16T12:00:00Z', reason: 'Reposición de prueba',
  source_establishment: source, destination_establishment: destination,
  lines: Array.from({ length: index === 1 ? 2 : 1 }, (_, line) => ({
    id: line + 1, description: 'Papel de prueba', unit_code: 'NIU', quantity: 10,
    cancelled: 0, assigned: 0, departed: 0, in_transit: 0, received: 0, pending_assignment: 10,
  })),
  dispatches: Array.from({ length: index % 3 }, (_, dispatch) => ({ id: dispatch + 1 })),
}));

async function openGuides(browser, baseURL, width, theme, { enabled = true, items = transfers } = {}) {
  const context = await browser.newContext({ baseURL, viewport: { width, height: 960 }, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
  await context.addInitScript((value) => {
    localStorage.setItem('token', 'internal-transfer-navigation-qa');
    localStorage.setItem('inkora-theme', value);
  }, theme);
  const page = await context.newPage();
  const unexpected = [];
  const listCalls = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/\/$/, '');
    let payload;
    if (request.method() === 'GET') {
      if (path === '/users/me') payload = { id: 73, tenant_id: 73, rol: 'admin', nombre_completo: 'Navegación QA', email: 'navigation@inkora.test', is_superadmin: false, must_change_password: false };
      else if (path === '/tenant/subscription-status') payload = { fiscal_feature_flags: { internal_transfers: enabled } };
      else if (path === '/sunat/exchange-rate') payload = { buy: 3.7, sell: 3.72 };
      else if (path === '/tenant') payload = { id: 73, business_name: 'Navegación QA', is_active: true };
      else if (['/guias-remision', '/clientes/page'].includes(path)) payload = emptyPage;
      else if (path === '/cotizaciones') payload = [];
      else if (path === '/inventario/almacenes') payload = [];
      else if (path === '/traslados-internos') {
        const skip = Number(url.searchParams.get('skip') || 0);
        const limit = Number(url.searchParams.get('limit') || 15);
        listCalls.push({ skip, limit });
        payload = { items: items.slice(skip, skip + limit), total: items.length, skip, limit };
      } else if (path === '/traslados-internos/1') payload = transfers[0];
    }
    if (payload === undefined) unexpected.push(`${request.method()} ${path}`);
    await route.fulfill({ status: payload === undefined ? 500 : 200, contentType: 'application/json', body: JSON.stringify(payload ?? { detail: 'Solicitud no prevista' }) });
  });
  const errors = attachCriticalErrorCollector(page);
  const originGuard = attachApiOriginGuard(page);
  await page.goto('/guias');
  return { context, page, unexpected, listCalls, errors, originGuard };
}

async function expectGuidesSelected(page) {
  const guideLink = page.locator('aside').getByRole('link', { name: 'Guías', exact: true });
  await expect(guideLink).toHaveClass(/\bis-active\b/);
  await expect(guideLink).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('aside .sidebar-item.is-active')).toHaveCount(1);
}

for (const width of [1440, 390]) {
  for (const theme of ['light', 'dark']) {
    test(`Guías abre la bandeja y conserva menú y datos separados a ${width}px ${theme}`, async ({ browser, baseURL }, testInfo) => {
      const { context, page, unexpected, listCalls, errors, originGuard } = await openGuides(browser, baseURL, width, theme);
      try {
        const entry = page.getByRole('link', { name: 'Traslados internos', exact: true });
        await expect(entry).toHaveAttribute('href', '/traslados-internos');
        await entry.click();
        await expect(page).toHaveURL(/\/traslados-internos$/);
        const rows = page.locator(width > 768 ? '.transfer-list__desktop tbody tr' : '.transfer-list-card');
        await expect(rows).toHaveCount(15);
        await expectGuidesSelected(page);
        await expect(page.getByText('Cada traslado puede incluir varios bienes y realizarse en uno o más viajes.', { exact: true })).toBeVisible();
        if (width > 768) {
          const firstCells = rows.first().getByRole('cell');
          await expect(firstCells.nth(0).locator('.ink-table-cell__primary')).toHaveText('TI-1');
          await expect(firstCells.nth(0).locator('time')).toHaveText('16/10/2026');
          await expect(firstCells.nth(1).locator('.ink-table-cell__primary')).toHaveText(source.name);
          await expect(firstCells.nth(1).locator('.ink-table-cell__meta')).toHaveText(`→ ${destination.name}`);
          await expect(firstCells.nth(2)).toHaveText('1');
          await expect(firstCells.nth(3)).toHaveText('0');
          await expect(rows.nth(1).getByRole('cell').nth(2)).toHaveText('2');
          await expect(rows.nth(1).getByRole('cell').nth(3)).toHaveText('1');
          await expect(rows.nth(2).getByRole('cell').nth(3)).toHaveText('2');
          const layout = await firstCells.evaluateAll((cells) => cells.slice(0, 2).map((cell) => {
            const primary = cell.querySelector('.ink-table-cell__primary').getBoundingClientRect();
            const meta = cell.querySelector('.ink-table-cell__meta').getBoundingClientRect();
            return { primaryBottom: primary.bottom, metaTop: meta.top };
          }));
          layout.forEach((cell) => expect(cell.metaTop).toBeGreaterThanOrEqual(cell.primaryBottom));
          await expect(page.locator('.transfer-list__mobile')).toBeHidden();
        } else {
          await expect(rows.first().getByRole('heading', { name: 'TI-1', exact: true })).toBeVisible();
          await expect(rows.first().locator('time')).toHaveText('16/10/2026');
          await expect(rows.first().locator('.transfer-list-card__route')).toContainText(source.name);
          await expect(rows.first().locator('.transfer-list-card__route')).toContainText(destination.name);
          await expect(rows.first().locator('.transfer-list-card__counts dd')).toHaveText(['1', '0']);
          await expect(rows.nth(1).locator('.transfer-list-card__counts dd')).toHaveText(['2', '1']);
          await expect(page.locator('.transfer-list__desktop')).toBeHidden();
        }
        const status = rows.nth(1).getByRole('button', { name: 'Pendiente: ayuda del estado', exact: true });
        const help = rows.nth(1).getByText('Hay bienes asignados a viajes. La salida aún no está confirmada.', { exact: true });
        await expect(status).toHaveAttribute('aria-expanded', 'false');
        await expect(help).toBeHidden();
        await status.click();
        await expect(status).toHaveAttribute('aria-expanded', 'true');
        await expect(help).toBeVisible();
        await page.screenshot({ path: testInfo.outputPath(`ayuda-estado-${width}-${theme}.png`), animations: 'disabled' });
        await status.press('Escape');
        await expect(help).toBeHidden();
        await status.press('Enter');
        await expect(help).toBeVisible();
        await status.press('Space');
        await expect(help).toBeHidden();
        await expect(status).toBeFocused();
        const detailContrast = await rows.first().getByRole('link', { name: 'Ver detalle', exact: true }).evaluate((link) => {
          const colors = [getComputedStyle(link).color, getComputedStyle(link.closest('.transfer-list-card') || link.closest('.transfer-list')).backgroundColor];
          const luminance = colors.map((color) => color.match(/[\d.]+/g).slice(0, 3).map((value) => {
            const channel = Number(value) / 255;
            return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
          }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0)).sort((a, b) => b - a);
          return (luminance[0] + 0.05) / (luminance[1] + 0.05);
        });
        expect(detailContrast).toBeGreaterThanOrEqual(4.5);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        await page.locator('.transfer-list__intro').click();
        await page.screenshot({ path: testInfo.outputPath(`bandeja-${width}-${theme}.png`), animations: 'disabled' });
        const pagination = page.getByRole('navigation', { name: 'Paginación', exact: true });
        await pagination.getByRole('button', { name: 'Página siguiente' }).click();
        await expect(rows).toHaveCount(1);
        await expect(rows.first()).toContainText('TI-16');
        await pagination.getByRole('button', { name: 'Página anterior' }).click();
        await expect(rows).toHaveCount(15);
        expect(listCalls.every((call) => call.limit === 15)).toBe(true);
        expect(listCalls).toContainEqual({ skip: 15, limit: 15 });
        expect(listCalls.at(-1)).toEqual({ skip: 0, limit: 15 });
        await page.getByRole('link', { name: 'Nuevo traslado', exact: true }).click();
        await expect(page).toHaveURL(/\/traslados-internos\/nuevo$/);
        await expectGuidesSelected(page);
        await page.getByRole('link', { name: 'Traslados', exact: true }).click();
        await expect(rows).toHaveCount(15);
        await rows.first().getByRole('link', { name: 'Ver detalle', exact: true }).click();
        await expect(page).toHaveURL(/\/traslados-internos\/1$/);
        await expect(page.locator('.internal-transfer-page').getByRole('heading', { name: 'Traslado TI-1', exact: true })).toBeVisible();
        await expectGuidesSelected(page);
        const menuButton = page.getByRole('button', { name: 'Abrir menú', exact: true });
        if (await menuButton.isVisible()) await menuButton.click();
        await page.locator('aside').getByRole('link', { name: 'Clientes', exact: true }).click();
        await expect(page.locator('aside').getByRole('link', { name: 'Clientes', exact: true })).toHaveAttribute('aria-current', 'page');
        await expect(page.locator('aside').getByRole('link', { name: 'Guías', exact: true })).not.toHaveAttribute('aria-current', 'page');
        await expect(page.locator('aside .sidebar-item.is-active')).toHaveCount(1);
        expect(unexpected).toEqual([]);
        errors.assertClean();
        originGuard.assertClean();
      } finally { await context.close(); }
    });
  }
}

test('el acceso respeta la habilitación por empresa y la bandeja vacía permite crear', async ({ browser, baseURL }) => {
  for (const enabled of [false, true]) {
    const { context, page, unexpected, errors } = await openGuides(browser, baseURL, 1440, 'light', { enabled, items: [] });
    try {
      await expect(page.locator('.document-list-empty')).toBeVisible();
      const entry = page.getByRole('link', { name: 'Traslados internos', exact: true });
      if (enabled) {
        await entry.click();
        await expect(page.getByRole('heading', { name: 'Aún no hay traslados internos' })).toBeVisible();
        await expect(page.getByRole('link', { name: 'Crear traslado', exact: true })).toHaveAttribute('href', '/traslados-internos/nuevo');
        await expectGuidesSelected(page);
      } else {
        await expect(entry).toHaveCount(0);
      }
      expect(unexpected).toEqual([]);
      errors.assertClean();
    } finally { await context.close(); }
  }
});

test('las fichas explican todos los estados y admiten nombres largos a 320px', async ({ browser, baseURL }, testInfo) => {
  const states = [
    ['draft', 'Borrador', 'La solicitud está creada y tiene bienes pendientes de asignar a un viaje.'],
    ['pending', 'Pendiente', 'Hay bienes asignados a viajes. La salida aún no está confirmada.'],
    ['in_transit', 'En tránsito', 'Hay bienes enviados que todavía están pendientes de recepción.'],
    ['partially_received', 'Recepción parcial', 'Se recibió una parte de los bienes solicitados. El traslado todavía no está completo.'],
    ['completed', 'Completado', 'Se completó la recepción de los bienes del traslado.'],
    ['cancelled', 'Cancelado', 'El traslado fue cancelado y no permite preparar nuevos viajes.'],
    ['unknown', 'Sin información', 'Revisa el detalle del traslado para consultar su situación.'],
  ];
  const items = states.map(([status], index) => ({ ...transfers[index], status,
    source_establishment: { ...source, name: `Depósito ${'de materiales '.repeat(10)}` },
    destination_establishment: { ...destination, name: `Establecimiento ${'de distribución '.repeat(8)}` },
  }));
  const { context, page, unexpected, errors } = await openGuides(browser, baseURL, 320, 'dark', { items });
  try {
    await page.getByRole('link', { name: 'Traslados internos', exact: true }).click();
    const cards = page.locator('.transfer-list-card');
    await expect(cards).toHaveCount(states.length);
    for (const [index, [, label, text]] of states.entries()) {
      const card = cards.nth(index);
      const status = card.getByRole('button', { name: `${label}: ayuda del estado`, exact: true });
      await status.click();
      await expect(card.getByText(text, { exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const bounds = await status.boundingBox();
      expect(bounds.height).toBeGreaterThanOrEqual(44);
      await status.press('Escape');
      await expect(status).toHaveAttribute('aria-expanded', 'false');
    }
    const motion = await cards.first().evaluate((card) => ({ name: getComputedStyle(card).animationName, duration: parseFloat(getComputedStyle(card).animationDuration) }));
    expect(motion.name).toBe('row-enter');
    expect(motion.duration).toBeLessThan(0.02);
    await cards.first().scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath('fichas-nombres-largos-320.png'), animations: 'disabled' });
    expect(unexpected).toEqual([]);
    errors.assertClean();
  } finally { await context.close(); }
});
