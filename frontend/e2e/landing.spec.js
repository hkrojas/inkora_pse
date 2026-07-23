import { expect, test } from '@playwright/test';

const viewports = [
  { width: 375, height: 812 },
  { width: 768, height: 900 },
  { width: 1024, height: 900 },
  { width: 1440, height: 900 },
];

for (const viewport of viewports) {
  test(`la entrada pública muestra la presentación a ${viewport.width}px`, async ({ browser, baseURL }) => {
    const context = await browser.newContext({
      baseURL,
      viewport,
      storageState: { cookies: [], origins: [] },
    });
    const page = await context.newPage();

    try {
      await page.goto('/');

      await expect(page).toHaveURL(/\/$/);
      await expect(page.getByRole('heading', { level: 1 })).toContainText('Vender es difícil');
      await expect(page.getByRole('link', { name: 'Solicitar acceso' }).first()).toBeVisible();

      const hasHorizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(hasHorizontalOverflow).toBe(false);
    } finally {
      await context.close();
    }
  });
}

test('el acceso directo al login sigue disponible', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, storageState: { cookies: [], origins: [] } });
  const page = await context.newPage();

  try {
    await page.goto('/login');
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('heading', { name: 'Bienvenido de vuelta' })).toBeVisible();
  } finally {
    await context.close();
  }
});

for (const viewport of viewports) {
  test(`la presentación mantiene su jerarquía a ${viewport.width}px`, async ({ browser, baseURL }) => {
    const context = await browser.newContext({
      baseURL,
      viewport,
      storageState: { cookies: [], origins: [] },
    });
    const page = await context.newPage();

    try {
      await page.goto('/presentacion');

      await expect(page).toHaveURL(/\/presentacion$/);
      await expect(page.locator('h1')).toHaveCount(1);
      await expect(page.getByRole('heading', { level: 1 })).toContainText('Vender es difícil');
      await expect(page.locator('.landing-header')).toHaveCSS('position', 'fixed');

      const layout = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        headerHeight: document.querySelector('.landing-header')?.getBoundingClientRect().height,
      }));
      expect(layout.scrollWidth).toBeLessThanOrEqual(layout.clientWidth);
      expect(layout.headerHeight).toBeGreaterThanOrEqual(77);
      expect(layout.headerHeight).toBeLessThanOrEqual(79);
    } finally {
      await context.close();
    }
  });
}

test('el encabezado se compacta y marca la sección visible', async ({ browser, baseURL }) => {
  const context = await browser.newContext({
    baseURL,
    viewport: { width: 1440, height: 900 },
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();

  try {
    await page.goto('/presentacion');
    const header = page.locator('.landing-header');

    await page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', { name: 'Cómo funciona', exact: true }).click();
    await expect(page).toHaveURL(/#recorrido$/);
    await expect(page.locator('.landing-nav > a.is-active')).toHaveText('Cómo funciona');
    await expect(header).toHaveClass(/is-scrolled/);

    const compactHeight = await header.evaluate((element) => element.getBoundingClientRect().height);
    expect(compactHeight).toBeGreaterThanOrEqual(63);
    expect(compactHeight).toBeLessThanOrEqual(65);

    const offsets = await page.evaluate(() => ({
      headerBottom: document.querySelector('.landing-header')?.getBoundingClientRect().bottom,
      sectionTop: document.querySelector('#recorrido')?.getBoundingClientRect().top,
    }));
    expect(offsets.sectionTop).toBeGreaterThanOrEqual(offsets.headerBottom - 1);
  } finally {
    await context.close();
  }
});

test('el menú móvil cierra con Escape', async ({ browser, baseURL }) => {
  const context = await browser.newContext({
    baseURL,
    viewport: { width: 375, height: 812 },
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();

  try {
    await page.goto('/presentacion');
    const menuButton = page.locator('.landing-menu-button');
    await menuButton.click();
    await expect(menuButton).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('.landing-nav')).toHaveClass(/is-open/);

    await page.keyboard.press('Escape');
    await expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('.landing-nav')).not.toHaveClass(/is-open/);
  } finally {
    await context.close();
  }
});

test('la presentación respeta movimiento reducido', async ({ browser, baseURL }) => {
  const context = await browser.newContext({
    baseURL,
    viewport: { width: 1024, height: 900 },
    reducedMotion: 'reduce',
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();

  try {
    await page.goto('/presentacion');
    const motion = await page.locator('.landing-workflow-preview__screen').evaluate((element) => ({
      animationDuration: getComputedStyle(element).animationDuration,
      opacity: getComputedStyle(element).opacity,
      transform: getComputedStyle(element).transform,
    }));
    expect(Number.parseFloat(motion.animationDuration)).toBeLessThanOrEqual(.00001);
    expect(motion.opacity).toBe('1');
    expect(motion.transform).toBe('none');
  } finally {
    await context.close();
  }
});
