import { test, expect } from '@playwright/test';

const API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000';

const tenant = {
  id: 7,
  business_name: 'PAPELERIA GRAFICA Y PUBLICITARIA SAC.',
  business_ruc: '20606751509',
  business_address: 'Av. Los Pinos 123',
  plan_type: 'founder',
  is_active: true,
  has_apisperu_token: true,
  apisperu_token_status: 'ok',
  has_smartpse_gre_credentials: true,
  smartpse_gre_status: 'ok',
  smartpse_gre_checked_at: '2026-05-05T16:00:00Z',
};

const user = {
  id: 700,
  email: 'visual.qa@inkora.test',
  nombre_completo: 'Visual QA',
  rol: 'admin',
  is_superadmin: false,
  must_change_password: false,
  tenant_id: tenant.id,
};

const smartPseGuide = {
  id: 6,
  tenant_id: tenant.id,
  serie: 'T001',
  correlativo: 5,
  fecha_emision: '2026-05-05T16:00:00Z',
  fecha_traslado: '2026-05-06',
  motivo_traslado: '01',
  modalidad_traslado: '02',
  peso_bruto_total: 12.5,
  unidad_medida_peso: 'KGM',
  partida_direccion: 'Av. Los Pinos 123, Lima',
  partida_ubigeo: '150101',
  llegada_direccion: 'Jr. El Sol 456, Ate',
  llegada_ubigeo: '150103',
  estado: 'pendiente_smartpse',
  sunat_hash: 'smoke-hash-smartpse-0005',
  sunat_ticket: 'T001-000005',
  sunat_cdr_url: '',
  actions: {
    validate: { enabled: false },
    edit: { enabled: false },
    cancel: { enabled: false },
    consult: { enabled: true },
    confirm_departure: { enabled: false },
    emit: { enabled: false },
  },
  items: [
    { id: 1, descripcion: 'Afiches publicitarios', cantidad: 100, unidad_medida: 'NIU' },
  ],
};

async function createVisualContext(browser, baseURL, role = 'tenant', options = {}) {
  const state = options.state || { guide: smartPseGuide, jobPolls: 0 };
  const context = await browser.newContext({
    baseURL,
    viewport: options.viewport,
    storageState: { cookies: [], origins: [] },
  });
  await context.addInitScript(() => {
    localStorage.setItem('token', 'visual-qa-token');
    sessionStorage.removeItem('token');
  });
  const page = await context.newPage();

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/\/$/, '');
    const payload = getApiPayload(path, role, route.request().method(), state);

    if (payload) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    });
  });

  return { context, page };
}

function getApiPayload(path, role, method = 'GET', state = { guide: smartPseGuide }) {
  if (path === '/users/me') {
    return role === 'superadmin'
      ? { ...user, rol: 'superadmin', is_superadmin: true, tenant_id: null }
      : user;
  }
  if (path === '/sunat/exchange-rate') return { buy: '3.512', sell: '3.522' };
  if (path === '/tenant/subscription-status') return {};
  if (path === '/tenant') {
    return {
      ...tenant,
      has_sunat_credentials: true,
      has_sunat_cert: true,
      has_smartpse_credentials: true,
      smartpse_status: 'ok',
    };
  }
  if (path === '/clientes' || path === '/cotizaciones') return [];
  if (path === '/guias-remision') {
    return {
      items: [state.guide],
      total: 1,
      counts: {
        all: 1,
        pending: 1,
        smartpse: 1,
        transit: 0,
        emitted: 0,
        cancelled: 0,
      },
    };
  }
  if (path === '/guias-remision/6/emitir' && method === 'POST') {
    return {
      success: true,
      queued: true,
      job_id: 77,
      job_status: 'queued',
    };
  }
  if (path === '/emission-jobs/77') {
    state.jobPolls = (state.jobPolls || 0) + 1;
    if (state.jobPolls >= 1) {
      state.guide = {
        ...state.guide,
        estado: 'emitida',
        cdr_disponible: true,
        xml_disponible: true,
        sunat_hash: 'accepted-gre-hash',
        actions: {
          ...state.guide.actions,
          emit: { enabled: false },
          consult: { enabled: false },
          confirm_departure: { enabled: true },
        },
      };
      return { id: 77, status: 'succeeded', last_error: null };
    }
    return { id: 77, status: 'queued', last_error: null };
  }
  if (path === '/guias-remision/6') return state.guide;
  if (path === '/superadmin/tenants-page') {
    return {
      items: [tenant],
      total: 1,
      skip: 0,
      limit: 25,
      metrics: {
        total: 1,
        active: 1,
        smartpse_gre: 1,
        smartpse_gre_pending: 0,
      },
    };
  }
  return null;
}

test.describe('Smart PSE GRE QA visual', () => {
  test('superadmin abre modal GRE sin exponer secretos guardados', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL, 'superadmin');

    try {
      await page.goto('/superadmin');
      await expect(page.getByRole('heading', { level: 2, name: /^Panel de empresas$/i })).toBeVisible();

      await page.getByRole('button', { name: /Más opciones para/i }).click();
      const credentialsButton = page.getByRole('button', { name: /^Credenciales de guías$/i });
      await expect(credentialsButton).toBeVisible();
      await credentialsButton.click();

      await expect(page.getByRole('heading', { name: /^Credenciales de guías$/i })).toBeVisible();
      await expect(page.getByRole('heading', { name: /^Conexión para emitir guías$/i })).toBeVisible();
      await expect(page.getByText(/los campos no se precargan/i)).toBeVisible();

      await expect(page.getByLabel(/usuario sol corto/i)).toHaveValue('');
      await expect(page.getByLabel(/clave sol/i)).toHaveValue('');
      await expect(page.getByLabel(/client id sunat/i)).toHaveValue('');
      await expect(page.getByLabel(/client secret sunat/i)).toHaveValue('');
    } finally {
      await context.close();
    }
  });

  test('bandeja y detalle de guias muestran evidencia Smart PSE sin credenciales', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL);

    try {
      await page.goto('/guias');
      await expect(page.getByRole('button', { name: /Smart PSE\s*1/i })).toBeVisible();
      await expect(page.getByText(/Pendiente Smart PSE/i).first()).toBeVisible();
      await expect(page.getByText(/XML firmado; CDR pendiente/i).first()).toBeVisible();

      await page.goto('/guias/6');
      await expect(page.getByRole('heading', { level: 2, name: /^Guía T001-000005$/i })).toBeVisible();
      await expect(page.getByRole('heading', { name: /smart pse/i })).toBeVisible();
      await expect(page.getByText(/^Hash$/i)).toBeVisible();
      await expect(page.getByText(/^Ticket$/i)).toBeVisible();
      await expect(page.locator('.smartpse-evidence-state', { hasText: 'CDR pendiente' })).toBeVisible();
      await expect(page.getByText(/clave SOL/i)).toHaveCount(0);
      await expect(page.getByText(/client secret/i)).toHaveCount(0);
    } finally {
      await context.close();
    }
  });

  test('una guía pendiente se encola y solo comunica aceptación después del CDR', async ({ browser, baseURL }) => {
    const state = {
      guide: {
        ...smartPseGuide,
        estado: 'pendiente',
        sunat_hash: null,
        sunat_ticket: null,
        cdr_disponible: false,
        xml_disponible: false,
        actions: {
          ...smartPseGuide.actions,
          consult: { enabled: false },
          emit: { enabled: true },
        },
      },
      jobPolls: 0,
    };
    const { context, page } = await createVisualContext(browser, baseURL, 'tenant', { state });

    try {
      await page.goto('/guias/6');
      const emitButton = page.getByRole('button', { name: /emitir a SUNAT/i });
      await expect(emitButton).toBeVisible();
      await emitButton.click();
      const emitDialog = page.getByRole('dialog', { name: 'Emitir guía de remisión' });
      await expect(emitDialog).toBeVisible();
      await emitDialog.getByRole('button', { name: 'Emitir guía' }).click();
      await expect(page.getByText(/Guía encolada para emisión fiscal/i)).toBeVisible();
      await expect(page.getByText('Emitida', { exact: true }).first()).toBeVisible({ timeout: 5000 });
      await expect(page.getByRole('button', { name: /emitir a SUNAT/i })).toHaveCount(0);
      await expect(page.getByText(/CDR disponible/i)).toBeVisible();
      await expect(page.getByText(/XML firmado y CDR definitivo disponibles/i)).toBeVisible();
    } finally {
      await context.close();
    }
  });

  test('configuracion tenant comunica credenciales fiscales gestionadas', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL);

    try {
      await page.goto('/configuracion');
      await page.getByRole('tab', { name: /Config\. Fiscal/i }).click();

      await expect(page.getByText(/Credenciales fiscales gestionadas/i)).toBeVisible();
      await expect(page.getByText(/Solo superadmin puede cargar o rotar credenciales GRE\/SUNAT/i)).toBeVisible();
      await expect(page.getByText(/^Credenciales SOL$/i)).toHaveCount(0);
      await expect(page.getByLabel(/usuario sol/i)).toHaveCount(0);
      await expect(page.getByLabel(/client secret/i)).toHaveCount(0);
    } finally {
      await context.close();
    }
  });

  test('rutas GRE clave son usables en mobile sin desborde horizontal', async ({ browser, baseURL }) => {
    const viewport = { width: 390, height: 844 };

    const superadmin = await createVisualContext(browser, baseURL, 'superadmin', { viewport });
    try {
      await superadmin.page.goto('/superadmin');
      await expect(superadmin.page.getByRole('heading', { level: 2, name: /^Panel de empresas$/i })).toBeVisible();
      await superadmin.page.getByRole('button', { name: /Más opciones para/i }).click();
      await superadmin.page.getByRole('button', { name: /^Credenciales de guías$/i }).click();
      await expect(superadmin.page.getByRole('heading', { name: /^Credenciales de guías$/i })).toBeVisible();
      await expectPageWithoutHorizontalOverflow(superadmin.page);
    } finally {
      await superadmin.context.close();
    }

    const tenantPages = await createVisualContext(browser, baseURL, 'tenant', { viewport });
    try {
      await tenantPages.page.goto('/guias');
      await expect(tenantPages.page.getByText(/Pendiente Smart PSE/i).first()).toBeVisible();
      await expectPageWithoutHorizontalOverflow(tenantPages.page);

      for (const width of [320, 390, 768, 1024]) {
        await tenantPages.page.setViewportSize({ width, height: 844 });
        const titleOverflow = await tenantPages.page.locator('.app-topbar h1').evaluate(
          (title) => title.scrollWidth - title.clientWidth,
        );
        expect(titleOverflow).toBeLessThanOrEqual(2);
        const guideLayout = await tenantPages.page.locator('.guide-table-list').evaluate((card) => {
          const table = card.querySelector('.guide-document-table');
          const row = table.querySelector('tbody tr');
          const action = row.querySelector('td:last-child a');
          return {
            cardWidth: card.getBoundingClientRect().width,
            tableWidth: table.getBoundingClientRect().width,
            rowHeight: row.getBoundingClientRect().height,
            actionRight: action.getBoundingClientRect().right,
          };
        });
        expect(guideLayout.tableWidth).toBeLessThanOrEqual(guideLayout.cardWidth + 2);
        expect(guideLayout.rowHeight).toBeLessThan(800);
        expect(guideLayout.actionRight).toBeLessThanOrEqual(width);
        if (process.env.RESPONSIVE_CAPTURE === '1' && [390, 1024].includes(width)) {
          await tenantPages.page.locator('.guide-table-list').screenshot({ path: `test-results/responsive-guides-${width}.png` });
        }
      }

      await tenantPages.page.setViewportSize(viewport);

      await tenantPages.page.goto('/guias/6');
      await expect(tenantPages.page.locator('.smartpse-evidence-state', { hasText: 'CDR pendiente' })).toBeVisible();
      await expectPageWithoutHorizontalOverflow(tenantPages.page);

      await tenantPages.page.goto('/configuracion');
      await expect(tenantPages.page.locator('.settings-command-card')).toBeVisible();
      const settingsLayout = await tenantPages.page.locator('main').evaluate((main) => {
        const right = main.getBoundingClientRect().left + main.clientWidth;
        const overflowing = [...main.querySelectorAll('*')]
          .filter((element) => element.getBoundingClientRect().right > right + 2)
          .slice(0, 8)
          .map((element) => ({
            tag: element.tagName,
            className: typeof element.className === 'string' ? element.className : '',
            excess: Math.round(element.getBoundingClientRect().right - right),
          }));
        return {
          overflow: main.scrollWidth - main.clientWidth,
          clientWidth: main.clientWidth,
          offsetWidth: main.offsetWidth,
          scrollWidth: main.scrollWidth,
          overflowing,
        };
      });
      expect(settingsLayout.overflow, JSON.stringify(settingsLayout)).toBeLessThanOrEqual(2);
      if (process.env.RESPONSIVE_CAPTURE === '1') {
        await tenantPages.page.screenshot({ path: 'test-results/responsive-settings-390.png' });
      }
      await tenantPages.page.getByRole('tab', { name: /Config\. Fiscal/i }).click();
      await expect(tenantPages.page.getByText(/Credenciales fiscales gestionadas/i)).toBeVisible();
      await expectPageWithoutHorizontalOverflow(tenantPages.page);
    } finally {
      await tenantPages.context.close();
    }
  });

  test('montos y acciones operativas caben en pantallas pequeñas', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL);
    const debt = {
      id: 42,
      cotizacion_id: 42,
      cliente_nombre: 'Cliente de prueba',
      internal_order_number: 'ORD-0001-000042',
      fecha_vencimiento: '2026-09-01',
      saldo_pendiente: 57484.01,
      dias_vencido: 25,
    };
    const stock = {
      product_id: 1,
      product_name: 'Producto de prueba',
      product_code: 'P-001',
      warehouse_id: 1,
      warehouse_name: 'Almacén central',
      unit: 'NIU',
      on_hand: 2872622.9996,
      committed: 0,
      available: 2872622.9996,
      status: 'ok',
      minimum_stock: 0,
    };
    const responses = {
      '/analytics/dashboard': { ingresos_totales: 19454.32 },
      '/cobranza/resumen': {
        total_pagado_mes: 314.83,
        total_por_cobrar: 57484.01,
        total_vencido: 26515.24,
        documentos_pendientes: 1,
        clientes_con_deuda: 1,
      },
      '/cobranza/vencidas': [debt],
      '/inventario/existencias': [stock],
      '/inventario/kardex/page': { items: [], total: 0 },
      '/inventario/almacenes': [{ id: 1, name: 'Almacén central', code: 'CENTRAL' }],
      '/inventario/establecimientos-fiscales': [],
      '/inventario/devoluciones': [],
    };

    await page.route(`${API_ORIGIN}/**`, async (route) => {
      const path = new URL(route.request().url()).pathname.replace(/\/$/, '');
      if (!(path in responses)) return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(responses[path]),
      });
    });

    try {
      for (const width of [1024, 768, 390, 320]) {
        await page.setViewportSize({ width, height: 850 });

        await page.goto('/dashboard');
        const dashboardValues = page.locator('[data-testid="dashboard-business-mockup"] .business-metric__value');
        await expect(dashboardValues.first()).toBeVisible();
        const dashboardOverflow = await dashboardValues.evaluateAll(
          (values) => values.map((value) => value.scrollWidth - value.clientWidth),
        );
        expect(Math.max(...dashboardOverflow)).toBeLessThanOrEqual(2);
        if (process.env.RESPONSIVE_CAPTURE === '1' && width === 390) {
          await page.locator('[data-testid="dashboard-business-mockup"] .business-metric').first().screenshot({ path: 'test-results/responsive-dashboard-390.png' });
        }

        await page.goto('/inventario');
        await expect(page.locator('.inventory-metric__value').last()).toBeVisible();
        const inventoryHeader = await page.locator('.inventory-page .operational-page-header').evaluate((header) => {
          const copy = header.querySelector('.operational-page-header__copy');
          const actions = header.querySelector('.operational-page-header__actions');
          const headerRect = header.getBoundingClientRect();
          const copyRect = copy.getBoundingClientRect();
          const actionsRect = actions.getBoundingClientRect();
          return {
            overflow: header.scrollWidth - header.clientWidth,
            copyWidth: copyRect.width,
            actionsRight: actionsRect.right,
            actionsBelowCopy: actionsRect.top >= copyRect.bottom - 2,
            headerRight: headerRect.right,
          };
        });
        expect(inventoryHeader.overflow).toBeLessThanOrEqual(2);
        expect(inventoryHeader.copyWidth).toBeGreaterThanOrEqual(Math.min(360, width - 48));
        expect(inventoryHeader.actionsRight).toBeLessThanOrEqual(inventoryHeader.headerRight + 2);
        expect(inventoryHeader.actionsBelowCopy).toBe(true);
        const inventoryOverflow = await page.locator('.inventory-metric__value').last().evaluate(
          (value) => value.scrollWidth - value.clientWidth,
        );
        expect(inventoryOverflow).toBeLessThanOrEqual(2);
        if (process.env.RESPONSIVE_CAPTURE === '1' && [390, 768, 1024].includes(width)) {
          await page.locator('.inventory-page .operational-page-header').screenshot({ path: `test-results/responsive-inventory-header-${width}.png` });
        }
        if (process.env.RESPONSIVE_CAPTURE === '1' && width === 390) {
          await page.locator('.inventory-metric').last().screenshot({ path: 'test-results/responsive-inventory-390.png' });
        }

        await page.goto('/cobranza');
        await expect(page.locator('.cobranza-row').first()).toBeVisible();
        const collectionLayout = await page.locator('.cobranza-list').evaluate((list) => ({
          overflow: list.scrollWidth - list.clientWidth,
          actionRight: list.querySelector('.cobranza-row .actions-col').getBoundingClientRect().right,
        }));
        expect(collectionLayout.overflow).toBeLessThanOrEqual(2);
        expect(collectionLayout.actionRight).toBeLessThanOrEqual(width);
        if (process.env.RESPONSIVE_CAPTURE === '1' && width === 390) {
          await page.locator('.cobranza-list').screenshot({ path: 'test-results/responsive-collections-390.png' });
        }
      }
    } finally {
      await context.close();
    }
  });
});

async function expectPageWithoutHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth - root.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(2);
}
