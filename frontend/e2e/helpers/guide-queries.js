import { expect } from '@playwright/test';

export async function expectInlineGuideQueries(page) {
  const rows = page.locator('.guide-query-control:visible');
  await expect(rows.first()).toBeVisible();
  expect(await rows.count()).toBeGreaterThan(0);
  for (const row of await rows.all()) {
    const input = row.locator('input');
    const button = row.getByRole('button');
    const [fieldBox, buttonBox] = await Promise.all([input.boundingBox(), button.boundingBox()]);
    expect(Math.abs(fieldBox.y - buttonBox.y)).toBeLessThanOrEqual(1);
    expect(Math.abs(fieldBox.height - buttonBox.height)).toBeLessThanOrEqual(1);
    expect(buttonBox.x).toBeGreaterThan(fieldBox.x);
    expect(fieldBox.width).toBeGreaterThan(90);
    expect(buttonBox.height).toBeGreaterThanOrEqual(44);
    await expect(button).toHaveText('Consultar');
    await expect(input).toHaveAccessibleName(/.+/);
    expect(await button.evaluate((element) => element.closest('label'))).toBeNull();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}
