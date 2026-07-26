import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const viewports = [
  { width: 375, height: 812 },
  { width: 768, height: 900 },
  { width: 1024, height: 900 },
  { width: 1440, height: 900 },
];

async function openPublicPage(browser, baseURL, viewport, path = '/') {
  const context = await browser.newContext({ baseURL, viewport, storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  await page.goto(path);
  return { context, page };
}

for (const viewport of viewports) {
  test(`la landing mantiene jerarquía y ancho a ${viewport.width}px`, async ({ browser, baseURL }) => {
    const { context, page } = await openPublicPage(browser, baseURL, viewport);
    try {
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(/De la cotización al cobro/);
      await expect(page.locator('h1')).toHaveCount(1);
      await expect(page.getByRole('link', { name: 'Solicitar acceso' }).first()).toBeVisible();
      await expect(page.locator('h2').first()).toHaveText('El hilo de una venta.');
      await expect(page.getByRole('heading', { name: 'Cinco datos. Una respuesta legible.' })).toBeAttached();
      await expect(page.getByRole('heading', { name: /Un solo plan/ })).toBeAttached();
      const layout = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
      expect(layout.scroll).toBeLessThanOrEqual(layout.client);
    } finally { await context.close(); }
  });
}

test('conserva las rutas públicas y los destinos de conversión', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 1440, height: 900 }, '/presentacion');
  try {
    await expect(page).toHaveURL(/\/presentacion$/);
    await expect(page.getByRole('link', { name: 'Solicitar acceso' }).first()).toHaveAttribute('href', '/solicitar-acceso');
    await expect(page.getByRole('link', { name: 'Iniciar sesión' }).first()).toHaveAttribute('href', '/login');
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', `${new URL(baseURL).origin}/`);
  } finally { await context.close(); }
});

test('la landing no descarga el shell autenticado ni fuentes remotas', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 375, height: 812 }, '/presentacion');
  try {
    const resources = await page.evaluate(() => performance.getEntriesByType('resource').map(({ name }) => name));
    expect(resources.some((url) => /globals(?:-|\.css)|fonts\.googleapis\.com|\/assets\/App-/.test(url))).toBe(false);
    expect(resources.some((url) => /LandingPage-.*\.css|\/src\/styles\/landing\.css/.test(url))).toBe(true);
  } finally { await context.close(); }
});

test('el modo oscuro respeta la preferencia, se puede cambiar y persiste', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 900 }, colorScheme: 'light', storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  try {
    await page.goto('/presentacion');
    await expect(page.locator('.landing-page')).toHaveAttribute('data-theme', 'light');
    await page.getByRole('button', { name: 'Cambiar a modo oscuro' }).click();
    await expect(page.locator('.landing-page')).toHaveAttribute('data-theme', 'dark');
    expect(await page.evaluate(() => localStorage.getItem('inkora-landing-theme'))).toBe('dark');
    await page.reload();
    await expect(page.locator('.landing-page')).toHaveAttribute('data-theme', 'dark');
    await expect(page.getByRole('button', { name: 'Cambiar a modo claro' })).toBeVisible();
  } finally { await context.close(); }
});

test('la sección de precio comunica un solo plan sin inventar una tarifa', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 1024, height: 900 }, '/presentacion');
  try {
    const pricing = page.locator('#precios');
    await expect(pricing.getByRole('heading', { name: /Un solo plan/ })).toBeVisible();
    await expect(pricing).toContainText(/Tarifa aún no publicada/i);
    await expect(pricing.getByRole('link', { name: 'Solicitar acceso' })).toHaveAttribute('href', '/solicitar-acceso');
  } finally { await context.close(); }
});

test('la consulta demuestra campos SUNAT, validación y resultado sin invocar una API', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 1440, height: 900 }, '/presentacion');
  const apiRequests = [];
  page.on('request', (request) => {
    if (['fetch', 'xhr'].includes(request.resourceType())) apiRequests.push(request.url());
  });
  try {
    const lookup = page.locator('#consulta');
    await expect(lookup.getByRole('heading', { name: 'Datos del comprobante' })).toBeVisible();
    await lookup.getByLabel('RUC del emisor').fill('123');
    await lookup.getByRole('button', { name: 'Consultar demostración' }).click();
    await expect(lookup.getByText('Ingresa los 11 dígitos del RUC emisor.')).toBeVisible();
    await expect(lookup.getByLabel('RUC del emisor')).toBeFocused();
    await expect(lookup.getByLabel('RUC del emisor')).toHaveAttribute('aria-describedby', 'lookup-ruc-error');
    await lookup.getByRole('button', { name: 'Usar datos de ejemplo' }).click();
    await expect(lookup.getByText('Completa la ficha y consulta.')).toBeVisible();
    await lookup.getByRole('button', { name: 'Consultar demostración' }).click();
    await expect(lookup.getByText('DEMOSTRACIÓN', { exact: true })).toBeVisible();
    await expect(lookup).toContainText('F001-00184');
    await lookup.getByLabel(/Importe total/).fill('499.00');
    await lookup.getByRole('button', { name: 'Consultar demostración' }).click();
    await expect(lookup.getByText('La consulta real aún no está conectada.')).toBeVisible();
    expect(apiRequests).toEqual([]);
  } finally { await context.close(); }
});

test('el login no recibe cambios funcionales', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 1280, height: 800 }, '/login');
  try {
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('heading', { name: 'Bienvenido de vuelta' })).toBeVisible();
  } finally { await context.close(); }
});

test('las anclas actualizan URL y estado activo', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 1440, height: 900 }, '/presentacion');
  try {
    const nav = page.getByRole('navigation', { name: 'Navegación principal' });
    await nav.getByRole('link', { name: 'Cómo funciona' }).click();
    await expect(page).toHaveURL(/#recorrido$/);
    await expect(nav.getByRole('link', { name: 'Cómo funciona' })).toHaveClass(/is-active/);
    await expect(page.locator('.landing-header')).toHaveClass(/is-scrolled/);
    const position = await page.evaluate(() => ({
      headerBottom: document.querySelector('.landing-header')?.getBoundingClientRect().bottom,
      sectionTop: document.querySelector('#recorrido')?.getBoundingClientRect().top,
    }));
    expect(position.sectionTop).toBeGreaterThanOrEqual(position.headerBottom - 1);
  } finally { await context.close(); }
});

test('el menú móvil bloquea scroll y cierra con Escape devolviendo el foco', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 375, height: 812 }, '/presentacion');
  try {
    const menu = page.locator('.landing-menu-button');
    await menu.click();
    await expect(menu).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('body')).toHaveCSS('overflow', 'hidden');
    await expect(page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', { name: 'Qué resuelve' })).toBeFocused();
    await page.keyboard.press('Shift+Tab');
    await expect(page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', { name: 'Solicitar acceso' })).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', { name: 'Qué resuelve' })).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button', { name: 'Abrir menú' })).toBeFocused();
    await expect(page.locator('body')).not.toHaveCSS('overflow', 'hidden');
  } finally { await context.close(); }
});

test('el recorrido funciona con flechas, Home y End', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 1024, height: 900 }, '/presentacion');
  try {
    const cotiza = page.getByRole('tab', { name: /Cotiza/ });
    await cotiza.focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('tab', { name: /Emite/ })).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('End');
    await expect(page.getByRole('tab', { name: /Cobra/ })).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('Home');
    await expect(cotiza).toHaveAttribute('aria-selected', 'true');
  } finally { await context.close(); }
});

test('movimiento reducido deja ruta y contenido visibles', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, viewport: { width: 1024, height: 900 }, reducedMotion: 'reduce', storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();
  try {
    await page.goto('/presentacion');
    await page.locator('.landing-route-line--hero path').waitFor({ state: 'attached' });
    const result = await page.evaluate(() => ({
      dash: getComputedStyle(document.querySelector('.landing-route-line--hero path')).strokeDashoffset,
      opacity: getComputedStyle(document.querySelector('.landing-hero-route li')).opacity,
      transform: getComputedStyle(document.querySelector('.landing-hero-route li')).transform,
    }));
    expect(Number.parseFloat(result.dash)).toBe(0);
    expect(result.opacity).toBe('1');
    expect(result.transform).toBe('none');
  } finally { await context.close(); }
});

test('mantiene lectura y reflujo al 200 por ciento', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 640, height: 900 }, '/presentacion');
  try {
    await page.evaluate(() => { document.documentElement.style.zoom = '200%'; });
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Solicitar acceso' }).first()).toBeVisible();
    const layout = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
    expect(layout.scroll).toBeLessThanOrEqual(layout.client);
  } finally { await context.close(); }
});

test('no presenta violaciones críticas o serias de accesibilidad', async ({ browser, baseURL }) => {
  const { context, page } = await openPublicPage(browser, baseURL, { width: 1440, height: 900 }, '/presentacion');
  try {
    const results = await new AxeBuilder({ page }).analyze();
    const severe = results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious');
    expect(severe).toEqual([]);
  } finally { await context.close(); }
});
