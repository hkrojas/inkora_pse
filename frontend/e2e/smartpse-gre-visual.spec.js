import { test, expect } from '@playwright/test';

const API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000';

const tenant = {
  id: 7,
  business_name: 'PAPELERIA GRAFICA Y PUBLICITARIA SAC.',
  business_ruc: '20606751509',
  business_address: 'Av. Los Pinos 123',
  logo_filename: 'https://assets.test/logo-inkora.png',
  payment_qr_filename: 'https://assets.test/qr-cobro.png',
  plan_type: 'founder',
  is_active: true,
  has_smartpse_credentials: true,
  smartpse_company_id: '7',
  smartpse_status: 'ok',
  smartpse_checked_at: '2026-05-05T16:00:00Z',
  smartpse_environment: 'demo',
  smartpse_remote_active: true,
  smartpse_remote_estado: 'ACTIVO',
  smartpse_remote_synced_at: '2026-05-05T16:00:00Z',
  smartpse_start_date: '2026-01-01T00:00:00Z',
  smartpse_end_date: null,
  smartpse_firmas_usadas: 4,
  has_smartpse_gre_credentials: true,
  smartpse_gre_status: 'ok',
  smartpse_gre_checked_at: '2026-05-05T16:00:00Z',
};

const createdTenant = {
  id: 22,
  business_name: 'DEMO SMART PSE SAC',
  business_ruc: '20609999991',
  business_address: 'Av. Demo 456',
  plan_type: 'founder',
  is_active: true,
  has_smartpse_credentials: false,
  smartpse_status: 'unchecked',
  smartpse_checked_at: null,
  smartpse_environment: 'demo',
  has_smartpse_gre_credentials: false,
  smartpse_gre_status: 'unchecked',
  smartpse_gre_checked_at: null,
};

const provisionedTenant = {
  ...createdTenant,
  has_smartpse_credentials: true,
  smartpse_company_id: '22',
  smartpse_status: 'ok',
  smartpse_checked_at: '2026-05-05T16:10:00Z',
  smartpse_environment: 'demo',
  smartpse_remote_active: true,
  smartpse_remote_estado: 'ACTIVO',
  smartpse_remote_synced_at: '2026-05-05T16:10:00Z',
  smartpse_start_date: '2026-01-01T00:00:00Z',
  smartpse_end_date: null,
  smartpse_firmas_usadas: 0,
};

const smartPseCompany = {
  id: '7',
  ruc: tenant.business_ruc,
  razon_social: tenant.business_name,
  environment: 'demo',
  active: true,
  estado: 'ACTIVO',
  start_date: '2026-01-01',
  end_date: null,
  firmas_usadas: 4,
  synced_at: '2026-05-05T16:12:00Z',
};

const productionPreparedTenant = {
  ...tenant,
  smartpse_environment: 'produccion',
  smartpse_remote_active: true,
  smartpse_remote_estado: 'ACTIVO',
  smartpse_remote_synced_at: '2026-05-05T16:20:00Z',
  smartpse_firmas_usadas: 5,
};

const inactiveSmartPseTenant = {
  ...productionPreparedTenant,
  smartpse_remote_active: false,
  smartpse_remote_estado: 'INACTIVO',
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
  items: [
    { id: 1, descripcion: 'Afiches publicitarios', cantidad: 100, unidad_medida: 'NIU' },
  ],
};

async function createVisualContext(browser, baseURL, role = 'tenant', options = {}) {
  const context = await browser.newContext({
    baseURL,
    viewport: options.viewport,
    storageState: { cookies: [], origins: [] },
  });
  await context.addInitScript(({ theme }) => {
    localStorage.setItem('token', 'visual-qa-token');
    if (theme) localStorage.setItem('inkora-theme', theme);
    sessionStorage.removeItem('token');
  }, { theme: options.theme || null });
  const page = await context.newPage();

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/\/$/, '');
    if (options.onRequest) await options.onRequest(route.request());

    const payload = getApiPayload(path, role, route.request());

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

function getApiPayload(path, role, request) {
  const method = request.method();
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
    };
  }
  if (path === '/users/upload-payment-qr' && method === 'POST') {
    return { url: 'https://assets.test/qr-cobro-actualizado.png' };
  }
  if (path === '/clientes' || path === '/cotizaciones') return [];
  if (path === '/clientes/page') return { items: [], total: 0 };
  if (path === '/facturas-emitidas/page') return { items: [], total: 0 };
  if (path === '/notas/page') {
    return {
      items: [],
      total: 0,
      counts: { all: 0, emitted: 0, pending: 0, rejected: 0, voided: 0 },
    };
  }
  if (path === '/guias-remision') {
    return {
      items: [smartPseGuide],
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
  if (path === '/guias-remision/6') return smartPseGuide;
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
  if (path === '/superadmin/tenants' && method === 'POST') return createdTenant;
  if (path === `/superadmin/tenants/${createdTenant.id}/smartpse/provision` && method === 'POST') {
    return provisionedTenant;
  }
  if (path === `/superadmin/tenants/${tenant.id}/smartpse/check` && method === 'POST') {
    return {
      valid: true,
      message: 'Credenciales Smart PSE aceptadas.',
      provider_status_code: 200,
      provider_detail: 'ok',
    };
  }
  if (path === `/superadmin/tenants/${tenant.id}/smartpse/company` && method === 'GET') {
    return smartPseCompany;
  }
  if (path === `/superadmin/tenants/${tenant.id}/smartpse/sync` && method === 'POST') {
    return tenant;
  }
  if (path === `/superadmin/tenants/${tenant.id}/smartpse/company` && method === 'PATCH') {
    return productionPreparedTenant;
  }
  if (path === `/superadmin/tenants/${tenant.id}/smartpse/activation` && method === 'POST') {
    return inactiveSmartPseTenant;
  }
  return null;
}

test.describe('Smart PSE GRE QA visual', () => {
  test('superadmin crea tenant y aprovisiona Smart PSE CPE sin ApisPeru', async ({ browser, baseURL }) => {
    const requests = [];
    const { context, page } = await createVisualContext(browser, baseURL, 'superadmin', {
      onRequest: async (request) => {
        const url = new URL(request.url());
        if (!url.pathname.startsWith('/superadmin')) return;
        let body = null;
        try {
          body = request.postDataJSON();
        } catch {
          body = null;
        }
        requests.push({ method: request.method(), path: url.pathname.replace(/\/$/, ''), body });
      },
    });

    try {
      await page.goto('/superadmin');
      await expect(page.getByRole('columnheader', { name: /Smart PSE CPE/i })).toBeVisible();
      await expect(page.getByText(/ApisPeru/i)).toHaveCount(0);

      await page.getByRole('button', { name: /Nuevo tenant/i }).first().click();
      await expect(page.locator('.ink-drawer')).toBeVisible();
      await expect(page.locator('.modal-panel')).toHaveCount(0);
      await expect(page.locator('form').getByText('Smart PSE CPE', { exact: true })).toBeVisible();
      await expect(page.getByText(/ApisPeru/i)).toHaveCount(0);

      await page.getByLabel(/Razon social/i).fill(createdTenant.business_name);
      await page.getByLabel(/^RUC/i).fill(createdTenant.business_ruc);
      await page.getByLabel(/Direccion fiscal/i).fill(createdTenant.business_address);
      await page.getByRole('button', { name: /Crear y aprovisionar/i }).click();

      await expect.poll(() =>
        requests.some((entry) => entry.path === `/superadmin/tenants/${createdTenant.id}/smartpse/provision`),
      ).toBe(true);

      const createRequest = requests.find((entry) => entry.path === '/superadmin/tenants' && entry.method === 'POST');
      expect(createRequest.body).toMatchObject({
        business_name: createdTenant.business_name,
        business_ruc: createdTenant.business_ruc,
        business_address: createdTenant.business_address,
      });
      expect(createRequest.body).not.toHaveProperty('apisperu_token');
      expect(createRequest.body).not.toHaveProperty('apisperu_url');

      const provisionRequest = requests.find(
        (entry) => entry.path === `/superadmin/tenants/${createdTenant.id}/smartpse/provision`,
      );
      expect(provisionRequest.body).toEqual({ environment: 'demo' });

      await page.getByRole('button', { name: /Verificar Smart PSE CPE/i }).first().click();
      await expect.poll(() =>
        requests.some((entry) => entry.path === `/superadmin/tenants/${tenant.id}/smartpse/check`),
      ).toBe(true);
    } finally {
      await context.close();
    }
  });

  test('superadmin abre drawer GRE sin exponer secretos guardados', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL, 'superadmin');

    try {
      await page.goto('/superadmin');
      await expect(page.getByRole('heading', { name: /Superadmin operativo/i })).toBeVisible();

      const firstGreButton = page.getByRole('button', { name: /^GRE$/ }).first();
      await expect(firstGreButton).toBeVisible();
      await firstGreButton.click();

      const drawer = page.locator('.ink-drawer.is-open');
      await expect(drawer).toBeVisible();
      await expect(drawer.getByRole('heading', { name: /Smart PSE GRE/i })).toBeVisible();
      await expect(page.getByText(/credenciales SUNAT para guias/i)).toBeVisible();
      await expect(page.getByText(/los campos no se precargan/i)).toBeVisible();

      await expect(page.getByLabel(/usuario sol corto/i)).toHaveValue('');
      await expect(page.getByLabel(/clave sol/i)).toHaveValue('');
      await expect(page.getByLabel(/client id sunat/i)).toHaveValue('');
      await expect(page.getByLabel(/client secret sunat/i)).toHaveValue('');
    } finally {
      await context.close();
    }
  });

  test('superadmin gestiona empresa Smart PSE CPE sin accion de eliminacion', async ({ browser, baseURL }) => {
    const requests = [];
    const { context, page } = await createVisualContext(browser, baseURL, 'superadmin', {
      onRequest: async (request) => {
        const url = new URL(request.url());
        if (!url.pathname.startsWith('/superadmin')) return;
        let body = null;
        try {
          body = request.postDataJSON();
        } catch {
          body = null;
        }
        requests.push({ method: request.method(), path: url.pathname.replace(/\/$/, ''), body });
      },
    });

    try {
      await page.goto('/superadmin');
      await page.getByRole('button', { name: /^Editar$/ }).first().click();

      const drawer = page.locator('.ink-drawer.is-open');
      await expect(drawer).toBeVisible();
      await expect(drawer.getByRole('heading', { name: /Empresa Smart PSE/i })).toBeVisible();
      await expect(drawer.getByText(/Eliminar SmartPSE|Eliminar Smart PSE/i)).toHaveCount(0);

      await drawer.getByRole('button', { name: /Ver empresa Smart PSE/i }).click();
      await expect.poll(() =>
        requests.some((entry) => entry.path === `/superadmin/tenants/${tenant.id}/smartpse/company` && entry.method === 'GET'),
      ).toBe(true);

      await drawer.getByRole('button', { name: /^Sincronizar$/i }).click();
      await expect.poll(() =>
        requests.some((entry) => entry.path === `/superadmin/tenants/${tenant.id}/smartpse/sync` && entry.method === 'POST'),
      ).toBe(true);

      await drawer.getByRole('button', { name: /^Demo$/ }).click();
      await page.getByRole('option', { name: /Produccion preparada/i }).click();
      await drawer.getByRole('button', { name: /Actualizar remoto/i }).click();
      await expect.poll(() =>
        requests.some(
          (entry) =>
            entry.path === `/superadmin/tenants/${tenant.id}/smartpse/company` &&
            entry.method === 'PATCH' &&
            entry.body?.environment === 'produccion',
        ),
      ).toBe(true);

      await drawer.getByRole('button', { name: /Desactivar remoto/i }).click();
      await expect.poll(() =>
        requests.some((entry) => entry.path === `/superadmin/tenants/${tenant.id}/smartpse/activation` && entry.method === 'POST'),
      ).toBe(true);
    } finally {
      await context.close();
    }
  });

  test('superadmin dark mode mantiene contraste en topbar y tabla', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL, 'superadmin', { theme: 'dark' });

    try {
      await page.goto('/superadmin');
      await expect(page.locator('html')).toHaveClass(/dark/);
      await expect(page.getByRole('heading', { name: /Superadmin operativo/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /Smart PSE CPE/i })).toBeVisible();

      const samples = await page.evaluate(() => {
        const channelAverage = (color) => {
          const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
          if (!match) return 255;
          return (Number(match[1]) + Number(match[2]) + Number(match[3])) / 3;
        };
        const readStyle = (selector, property = 'backgroundColor') => {
          const element = document.querySelector(selector);
          return element ? getComputedStyle(element)[property] : 'rgb(255, 255, 255)';
        };

        return {
          topbarBg: channelAverage(readStyle('.app-route-superadmin .app-topbar')),
          filterBg: channelAverage(readStyle('.superadmin-filter-bar')),
          rowBg: channelAverage(readStyle('.superadmin-tenants-table tbody td')),
          titleColor: channelAverage(readStyle('.app-route-superadmin .app-topbar h1', 'color')),
          tenantNameColor: channelAverage(readStyle('.superadmin-tenant-name', 'color')),
        };
      });

      expect(samples.topbarBg).toBeLessThan(90);
      expect(samples.filterBg).toBeLessThan(110);
      expect(samples.rowBg).toBeLessThan(110);
      expect(samples.titleColor).toBeGreaterThan(160);
      expect(samples.tenantNameColor).toBeGreaterThan(160);
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
      await expect(page.getByRole('heading', { name: /guia/i })).toBeVisible();
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

  test('configuracion tenant comunica credenciales fiscales gestionadas', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL);

    try {
      await page.goto('/configuracion');
      await page.getByRole('button', { name: /fiscal/i }).click();

      await expect(page.getByText(/Credenciales fiscales gestionadas/i)).toBeVisible();
      await expect(page.getByText(/Solo superadmin puede cargar o rotar credenciales GRE\/SUNAT/i)).toBeVisible();
      await expect(page.getByText(/^Credenciales SOL$/i)).toHaveCount(0);
      await expect(page.getByLabel(/usuario sol/i)).toHaveCount(0);
      await expect(page.getByLabel(/client secret/i)).toHaveCount(0);
    } finally {
      await context.close();
    }
  });

  test('configuracion muestra logo y QR de cobro del tenant', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL);

    try {
      await page.goto('/configuracion');
      await expect(page.getByRole('img', { name: /Logo PAPELERIA/i }).first()).toBeVisible();
      await expect(page.getByRole('img', { name: /QR de cobro PAPELERIA/i }).first()).toBeVisible();

      const [fileChooser] = await Promise.all([
        page.waitForEvent('filechooser'),
        page.getByRole('button', { name: /Subir captura QR/i }).click(),
      ]);
      await fileChooser.setFiles({
        name: 'qr-cobro.png',
        mimeType: 'image/png',
        buffer: Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=',
          'base64',
        ),
      });

      await expect(page.getByRole('heading', { name: /Recortar QR de cobro/i })).toBeVisible();
      await page.getByRole('button', { name: /Guardar QR limpio/i }).click();
      await expect(page.getByRole('img', { name: /QR de cobro PAPELERIA/i }).first()).toHaveAttribute(
        'src',
        /qr-cobro-actualizado\.png/,
      );
    } finally {
      await context.close();
    }
  });

  test('formularios de guia y nota nueva abren como drawer lateral', async ({ browser, baseURL }) => {
    const { context, page } = await createVisualContext(browser, baseURL);

    try {
      await page.goto('/guias');
      await page.getByRole('button', { name: /Nueva gu[ií]a/i }).first().click();
      await expect(page.locator('.ink-drawer.is-open')).toBeVisible();
      await expect(page.locator('.ink-drawer.is-open').getByRole('heading', { name: /Nueva gu[ií]a de remisi[oó]n/i })).toBeVisible();
      await expect(page.locator('.modal-panel')).toHaveCount(0);
      await page.locator('.ink-drawer-close').click();
      await expect(page.locator('.ink-drawer.is-open')).toHaveCount(0);

      await page.goto('/notas');
      await page.getByRole('button', { name: /Nueva nota/i }).first().click();
      await expect(page.locator('.ink-drawer.is-open')).toBeVisible();
      await expect(page.locator('.ink-drawer.is-open').getByRole('heading', { name: /Nueva nota de cr[eé]dito \/ d[eé]bito/i })).toBeVisible();
      await expect(page.locator('.modal-panel')).toHaveCount(0);
    } finally {
      await context.close();
    }
  });

  test('rutas GRE clave son usables en mobile sin desborde horizontal', async ({ browser, baseURL }) => {
    const viewport = { width: 390, height: 844 };

    const superadmin = await createVisualContext(browser, baseURL, 'superadmin', { viewport });
    try {
      await superadmin.page.goto('/superadmin');
      await expect(superadmin.page.getByRole('heading', { name: /Superadmin operativo/i })).toBeVisible();
      await superadmin.page.getByRole('button', { name: /^GRE$/ }).first().click();
      await expect(superadmin.page.locator('.ink-drawer.is-open')).toBeVisible();
      await expect(superadmin.page.getByRole('heading', { name: /Smart PSE GRE/i })).toBeVisible();
      await expectPageWithoutHorizontalOverflow(superadmin.page);
    } finally {
      await superadmin.context.close();
    }

    const tenantPages = await createVisualContext(browser, baseURL, 'tenant', { viewport });
    try {
      await tenantPages.page.goto('/guias');
      await expect(tenantPages.page.getByText(/Pendiente Smart PSE/i).first()).toBeVisible();
      await expectPageWithoutHorizontalOverflow(tenantPages.page);

      await tenantPages.page.goto('/guias/6');
      await expect(tenantPages.page.locator('.smartpse-evidence-state', { hasText: 'CDR pendiente' })).toBeVisible();
      await expectPageWithoutHorizontalOverflow(tenantPages.page);

      await tenantPages.page.goto('/configuracion');
      await tenantPages.page.getByRole('button', { name: /fiscal/i }).click();
      await expect(tenantPages.page.getByText(/Credenciales fiscales gestionadas/i)).toBeVisible();
      await expectPageWithoutHorizontalOverflow(tenantPages.page);
    } finally {
      await tenantPages.context.close();
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
