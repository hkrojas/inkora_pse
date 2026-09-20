import { expect, test } from '@playwright/test';

test.describe('almacenes con datos fiscales integrados', () => {
  test('configura, verifica y conserva los datos SUNAT desde Inventario', async ({ page }) => {
    await page.goto('/inventario?tab=warehouses');
    await expect(page.getByRole('heading', { name: 'Inventario' })).toBeVisible();

    const activateButton = page.getByRole('button', { name: 'Activar inventario' });
    if (await activateButton.isVisible()) {
      await activateButton.click();
      await expect(page.getByText('Inventario activado.')).toBeVisible();
    }

    const primaryWarehouse = page.locator('.inventory-warehouse-card').filter({
      hasText: 'Almacén principal',
    });
    await expect(primaryWarehouse).toBeVisible();
    await primaryWarehouse.getByRole('button', { name: 'Editar' }).click();

    const editDialog = page.getByRole('dialog', { name: 'Editar almacén' });
    await expect(editDialog).toBeVisible();
    await editDialog.getByLabel('Dirección completa').fill('Av. Demo 123, Lima, Lima');
    await editDialog.getByLabel('Código de local SUNAT').fill('0000');
    await editDialog.getByLabel('Ubigeo').fill('150101');
    await editDialog.getByRole('checkbox', { name: 'Local principal ante SUNAT' }).check();
    await editDialog.getByRole('button', { name: 'Guardar cambios' }).click();

    await expect(page.getByText('Almacén actualizado.')).toBeVisible();
    await expect(primaryWarehouse.getByText('Datos SUNAT pendientes de verificar')).toBeVisible();
    await expect(primaryWarehouse.getByText('0000 · Ubigeo 150101')).toBeVisible();

    await primaryWarehouse.getByRole('button', { name: 'Verificar' }).click();
    const verifyDialog = page.getByRole('dialog', { name: 'Verificar almacén' });
    await expect(verifyDialog).toBeVisible();
    await verifyDialog.getByLabel('Evidencia o criterio de verificación').fill(
      'Datos contrastados en una prueba local con ficha RUC sintética.',
    );
    await verifyDialog.getByRole('button', { name: 'Confirmar verificación' }).click();

    await expect(page.getByText('Datos SUNAT del almacén verificados.')).toBeVisible();
    await expect(primaryWarehouse.getByText('Datos SUNAT verificados')).toBeVisible();

    await page.getByRole('button', { name: 'Añadir almacén' }).click();
    const createDialog = page.getByRole('dialog', { name: 'Crear almacén' });
    await createDialog.getByLabel('Código interno').fill('ANEXO-01');
    await createDialog.getByLabel('Nombre').fill('Almacén anexo');
    await createDialog.getByLabel('Dirección completa').fill('Jr. Demo 456, Lima, Lima');
    await createDialog.getByLabel('Código de local SUNAT').fill('0001');
    await createDialog.getByLabel('Ubigeo').fill('150101');
    await createDialog.getByRole('button', { name: 'Crear almacén' }).click();

    await expect(page.getByText('Almacén creado.')).toBeVisible();
    const secondaryWarehouse = page.locator('.inventory-warehouse-card').filter({
      hasText: 'Almacén anexo',
    });
    await expect(secondaryWarehouse).toBeVisible();
    await expect(secondaryWarehouse.getByText('0001 · Ubigeo 150101')).toBeVisible();
    await expect(page.getByText('2 almacenes')).toBeVisible();
  });
});
