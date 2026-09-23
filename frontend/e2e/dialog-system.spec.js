import { expect, test } from '@playwright/test';

test.describe('diálogos propios de Inkora', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('confirma, cancela y decide sin abrir diálogos nativos', async ({ page }) => {
    const nativeDialogs = [];
    page.on('dialog', (dialog) => {
      nativeDialogs.push(dialog.type());
      dialog.dismiss();
    });

    await page.goto('/e2e/dialog-system.html');

    await page.getByRole('button', { name: 'Confirmación destructiva' }).click();
    const dangerDialog = page.getByRole('dialog', { name: 'Eliminar cotización' });
    await expect(dangerDialog).toBeVisible();
    await expect(dangerDialog.getByText('COT-000277')).toBeVisible();
    await expect(dangerDialog.getByRole('button', { name: 'Cancelar' })).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(dangerDialog).toBeHidden();
    await expect(page.getByText('Resultado: confirmar:false')).toBeVisible();

    await page.getByRole('button', { name: 'Decisión explícita' }).click();
    const decisionDialog = page.getByRole('dialog', { name: '¿Dónde guardar los cambios?' });
    await expect(decisionDialog).toBeVisible();
    await decisionDialog.getByRole('button', { name: 'Solo este comprobante' }).click();
    await expect(page.getByText('Resultado: decisión:document')).toBeVisible();

    await page.getByRole('button', { name: 'Copiar enlace' }).click();
    const copyDialog = page.getByRole('dialog', { name: 'Copiar enlace de cotización' });
    await expect(copyDialog).toBeVisible();
    await expect(copyDialog.getByRole('textbox', { name: 'Enlace público' })).toHaveValue(
      'https://inkora.example/cotizaciones/COT-000277',
    );
    await copyDialog.locator('button.btn-secondary').click();
    await expect(page.getByText('Resultado: copiar:false')).toBeVisible();

    expect(nativeDialogs).toEqual([]);
  });

  test('mantiene acciones visibles en pantalla móvil', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/e2e/dialog-system.html');
    await page.getByRole('button', { name: 'Confirmación destructiva' }).click();
    const dialog = page.getByRole('dialog', { name: 'Eliminar cotización' });
    await expect(dialog.getByRole('button', { name: 'Cancelar' })).toBeInViewport();
    await expect(dialog.getByRole('button', { name: 'Eliminar cotización' })).toBeInViewport();
  });

  test('la eliminación de cotización usa el diálogo compartido en la pantalla real', async ({ page }) => {
    await page.goto('/e2e/action-consistency.html');
    await page.getByRole('link', { name: 'Cotizaciones' }).click();
    await expect(page.getByText('COT-000277').first()).toBeVisible();
    await page.getByRole('button', { name: /Más acciones de COT-000277/i }).click();
    await page.getByRole('button', { name: 'Eliminar', exact: true }).click();

    const dialog = page.getByRole('dialog', { name: 'Eliminar cotización' });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('COT-000277')).toBeVisible();
    await dialog.getByRole('button', { name: 'Cancelar' }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText('COT-000277').first()).toBeVisible();
  });
});
