import { expect } from '@playwright/test';

export async function chooseInkoraOption(page, label, option) {
  await page.getByRole('button', { name: label, exact: true }).click();
  const listbox = page.getByRole('listbox', { name: label, exact: true });
  await expect(listbox).toBeVisible();
  await listbox.getByRole('option', { name: option, exact: true }).click();
  await expect(listbox).toHaveCount(0);
}

export function inkoraDayLabel(iso, month = 'long') {
  return new Intl.DateTimeFormat('es-PE', { day: 'numeric', month, year: 'numeric' })
    .format(new Date(`${iso}T12:00:00Z`));
}

export async function chooseInkoraDate(page, label, iso) {
  await page.getByRole('button', { name: label, exact: true }).click();
  const calendar = page.getByRole('dialog', { name: 'Seleccionar fecha', exact: true });
  await expect(calendar).toBeVisible();
  await calendar.getByRole('button', { name: inkoraDayLabel(iso), exact: true }).click();
  await expect(calendar).toHaveCount(0);
}

export async function chooseInkoraMonth(page, label, month) {
  await page.getByRole('button', { name: label, exact: true }).click();
  const calendar = page.getByRole('dialog', { name: 'Seleccionar mes', exact: true });
  await expect(calendar).toBeVisible();
  const date = new Date(`${month}-01T12:00:00Z`);
  const name = date.toLocaleDateString('es-PE', { month: 'long' });
  await calendar.getByRole('button', { name: `${name.charAt(0).toUpperCase()}${name.slice(1)} ${date.getUTCFullYear()}`, exact: true }).click();
  await expect(calendar).toHaveCount(0);
}

export async function expectPopupWithinViewport(page, popup) {
  await expect(popup).toBeVisible();
  const bounds = await popup.boundingBox();
  const viewport = page.viewportSize();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.y).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width + 1);
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height + 1);
}
