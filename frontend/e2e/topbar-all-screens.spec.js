import { test, expect } from '@playwright/test';
import { attachCriticalErrorCollector } from './helpers/assertions';

const apiOrigin = new URL(process.env.E2E_API_URL || 'http://localhost:8000').origin;
const screens = [
  ['/dashboard', 'Resumen'], ['/clientes', 'Clientes'], ['/productos', 'Productos'],
  ['/inventario', 'Inkora'], ['/cotizaciones', 'Cotizaciones'],
  ['/cotizaciones/42', 'Detalle de cotización'], ['/cobranza', 'Cobranza'],
  ['/comprobantes/nuevo', 'Crear comprobante'], ['/comprobantes/nuevo?tipo=03', 'Crear comprobante'],
  ['/facturas', 'Facturas'], ['/boletas', 'Boletas'], ['/guias', 'Guías de remisión'],
  ['/guias/nueva', 'Nueva guía'], ['/guias/nueva-transportista', 'Nueva guía transportista'],
  ['/guias/42/editar', 'Editar guía'], ['/guias/42', 'Detalle de guía'],
  ['/traslados-internos', 'Traslados internos'], ['/traslados-internos/nuevo', 'Nuevo traslado interno'],
  ['/traslados-internos/42', 'Detalle del traslado'], ['/inventario/establecimientos', 'Inkora'],
  ['/notas', 'Notas crédito/débito'], ['/notas/nueva', 'Inkora'],
  ['/retenciones', 'Retenciones'], ['/percepciones', 'Percepciones'],
  ['/resumen-diario', 'Resumen diario'], ['/bajas', 'Bajas'], ['/reversiones', 'Reversiones'],
  ['/configuracion', 'Configuración'], ['/cambiar-password', 'Configuración'],
  ['/diseno-pdf', 'Diseño PDF'], ['/superadmin', 'Superadmin'],
];
const emptyPage = { items: [], total: 0, skip: 0, limit: 15, counts: {} };
const establishment = { id: 1, name: 'Principal QA', address: 'Dirección sintética', sunat_code: '0000', ubigeo: '150101', is_active: true };
const quote = { id: 42, document_kind: 'quotation', estado: 'borrador', correlativo: 42,
  document_number: 'COT-000042', moneda: 'PEN', fecha_emision: '2026-10-07',
  cliente: { id: 1, razon_social: 'Cliente sintético', numero_documento: '20999999999' },
  items: [], detalles: [], total_venta: 0, total_gravadas: 0, total_igv: 0, pagos: [], cuotas_pago: [] };
const guide = { id: 42, dispatch_id: 42, fiscal_document_id: 42, serie: 'T001', correlativo: 42,
  estado: 'borrador', fecha_emision: '2026-10-07', fecha_traslado: '2026-10-07',
  motivo_traslado: '01', modalidad_traslado: '02', peso_bruto_total: 1, items: [], detalles: [] };
const payloads = {
  '/tenant': { id: 74, business_name: 'Encabezado QA', business_ruc: '20999999999', is_active: true, inventory_enabled: true },
  '/tenant/subscription-status': { fiscal_feature_flags: { retentions: true, perceptions: true, daily_summary: true, reversions: true, guides: true, internal_transfers: true } },
  '/sunat/exchange-rate': { buy: 3.7, sell: 3.72 },
  '/clientes/page': emptyPage, '/productos/page': emptyPage, '/cotizaciones/page': emptyPage,
  '/cotizaciones': [], '/clientes': [], '/productos': [],
  '/facturas-emitidas/page': emptyPage, '/notas/page': emptyPage,
  '/retenciones/page': emptyPage, '/percepciones/page': emptyPage,
  '/resumen-diario/page': emptyPage, '/reversiones/page': emptyPage,
  '/guias-remision': emptyPage, '/traslados-internos': emptyPage,
  '/inventario/almacenes': [establishment], '/inventario/establecimientos-fiscales': [],
  '/inventario/existencias': [], '/inventario/kardex/page': emptyPage, '/inventario/devoluciones/page': emptyPage,
  '/establecimientos': [establishment], '/cobranza/resumen': { total_por_cobrar: 0, documentos_vencidos: 0, total_pagado_mes: 0 },
  '/cobranza/vencidas/page': emptyPage, '/cobranza/vencidas': [],
  '/cotizaciones/42': quote, '/cotizaciones/42/pagos': [],
  '/guias-remision/42': guide, '/despachos/42': { version: 1, lines: [] },
  '/facturacion/comprobantes/42/despacho-contexto': { source_document: { id: 42, label: 'Factura', number: 'F001-000042' }, customer: {}, lines: [], eligibility: { can_prepare: true } },
  '/traslados-internos/42': { id: 42, status: 'draft', reason: 'Traslado sintético', lines: [], dispatches: [], source_establishment: establishment, destination_establishment: { ...establishment, id: 2 } },
  '/superadmin/tenants-page': { ...emptyPage, metrics: { total: 0, active: 0, smartpse_gre: 0, smartpse_gre_pending: 0 } },
  '/superadmin/access-requests': emptyPage,
  '/superadmin/smartpse/companies': { companies: [], pagination: { current_page: 1, last_page: 1, total: 0 } },
  '/analytics/dashboard/business': { meta: { currency: 'PEN', period: {}, comparison: {}, history: {} }, summary: {},
    history: [], products: [], clients: [], conversion: { available: false }, follow_up: {}, pending: {} },
};

for (const theme of ['light', 'dark']) {
  for (const width of [320, 360, 380, 390, 640, 768, 1024, 1440]) {
    test(`todas las pantallas: encabezado ${theme} a ${width}px`, async ({ browser, baseURL }, testInfo) => {
      test.setTimeout(120_000);
      const context = await browser.newContext({ baseURL, viewport: { width, height: 900 }, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
      await context.addInitScript((themeValue) => {
        localStorage.setItem('token', 'offline-all-screens-qa');
        localStorage.setItem('inkora-theme', themeValue);
      }, theme);
      const page = await context.newPage();
      const errors = attachCriticalErrorCollector(page);
      const unexpected = [];
      let currentPath;
      await page.route('**/*', async (route) => {
        const request = route.request(), url = new URL(request.url());
        if (!['fetch', 'xhr'].includes(request.resourceType())) {
          if (url.origin === new URL(baseURL).origin || ['data:', 'blob:'].includes(url.protocol)) await route.continue();
          else { unexpected.push(request.url()); await route.abort(); }
          return;
        }
        const path = url.pathname.replace(/\/$/, '');
        const payload = path === '/users/me'
          ? { id: 9, tenant_id: 74, rol: currentPath === '/superadmin' ? 'superadmin' : 'admin', is_active: true,
            is_superadmin: currentPath === '/superadmin', nombre_completo: 'Encabezado QA', email: 'qa@inkora.test', must_change_password: false }
          : payloads[path];
        if (url.origin !== apiOrigin || request.method() !== 'GET' || payload === undefined) {
          unexpected.push(`${currentPath}: ${request.method()} ${path}`); await route.abort(); return;
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
      });
      const reviewed = [];
      try {
        for (const [path, text] of screens) {
          currentPath = path;
          await page.goto(path);
          const title = page.locator('.app-topbar__title').locator('h1, p');
          await expect(title).toHaveText(text);
          await expect(page.getByText('Cargando...', { exact: true })).toHaveCount(0);
          await expect(page.locator('main').first()).toBeVisible();
          const header = page.locator('.app-topbar');
          const notifications = header.getByRole('button', { name: 'Ver notificaciones', exact: true });
          const [heading, titleBlock, action, bounds] = await Promise.all([title.boundingBox(), page.locator('.app-topbar__title').boundingBox(), notifications.boundingBox(), header.boundingBox()]);
          expect(Math.abs(titleBlock.y + titleBlock.height / 2 - action.y - action.height / 2), path).toBeLessThan(2);
          expect(heading.x + heading.width, path).toBeLessThanOrEqual(action.x - 3);
          expect(heading.width, path).toBeGreaterThan(20);
          expect(bounds.height, path).toBeLessThanOrEqual(width < 640 ? 80 : 145);
          const controls = header.getByRole('button').filter({ visible: true });
          for (const button of await controls.all()) {
            const box = await button.boundingBox();
            expect(box.x + box.width, path).toBeLessThanOrEqual(width + 1);
            expect(box.x, path).toBeGreaterThanOrEqual(bounds.x);
          }
          if (width < 1024) {
            const menu = page.getByRole('button', { name: 'Abrir menú', exact: true });
            const box = await menu.boundingBox();
            expect(heading.x, path).toBeGreaterThanOrEqual(box.x + box.width + 3);
            await menu.click();
            await page.getByRole('button', { name: 'Cerrar menú', exact: true }).click();
          }
          await page.screenshot({ path: testInfo.outputPath(`${path.replace(/[^a-zA-Z0-9]/g, '-')}.png`), animations: 'disabled' });
          reviewed.push({ path, width, theme, heading, header: bounds });
          expect(unexpected, path).toEqual([]);
          errors.assertClean();
        }
        await testInfo.attach('pantallas-revisadas', { body: JSON.stringify(reviewed, null, 2), contentType: 'application/json' });
      } finally { await context.close(); }
    });
  }
}

for (const theme of ['light', 'dark']) {
  for (const width of [320, 1440]) {
    test(`pantallas públicas ${theme} a ${width}px conservan su encabezado propio`, async ({ browser, baseURL }) => {
      test.setTimeout(90_000);
      const context = await browser.newContext({ baseURL, viewport: { width, height: 900 }, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
      await context.addInitScript(value => localStorage.setItem('inkora-theme', value), theme);
      const page = await context.newPage();
      const errors = attachCriticalErrorCollector(page);
      const writes = [];
      await page.route('**/*', async route => {
        if (!['GET', 'HEAD', 'OPTIONS'].includes(route.request().method())) {
          writes.push(route.request().method()); await route.abort();
        } else await route.continue();
      });
      try {
        for (const path of ['/', '/presentacion', '/login', '/recuperar-password', '/solicitar-acceso']) {
          await page.goto(path);
          await expect(page.locator('#root')).toBeVisible();
          await expect(page.getByText('Cargando...', { exact: true })).toHaveCount(0);
          await expect.poll(() => page.locator('#root').innerText()).toMatch(/.{40}/s);
          await expect(page.locator('.app-topbar')).toHaveCount(0);
          errors.assertClean();
        }
        expect(writes).toEqual([]);
      } finally { await context.close(); }
    });
  }
}
