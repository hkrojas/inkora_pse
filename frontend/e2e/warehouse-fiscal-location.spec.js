import { expect, test } from '@playwright/test';

test.describe('almacenes con datos fiscales integrados', () => {
  test('vincula varios almacenes con el establecimiento SUNAT persistido', async ({ page }) => {
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
    await expect(editDialog.getByLabel('Código de local SUNAT')).toHaveCount(0);
    await expect(editDialog.getByLabel('Ubigeo')).toHaveCount(0);
    await editDialog.getByLabel('Dirección interna (opcional)').fill('Stand demo 1023');
    await editDialog.getByLabel('Establecimiento SUNAT del almacén').click();
    await page.getByRole('option', { name: /0000 · Establecimiento principal · 150101/ }).click();
    await editDialog.getByRole('button', { name: 'Guardar cambios' }).click();

    await expect(page.getByText('Almacén actualizado.')).toBeVisible();
    await expect(primaryWarehouse.getByText('Datos SUNAT verificados')).toBeVisible();
    await expect(primaryWarehouse.getByText('0000 · Ubigeo 150101')).toBeVisible();

    await page.getByRole('button', { name: 'Añadir almacén' }).click();
    const createDialog = page.getByRole('dialog', { name: 'Crear almacén' });
    await createDialog.getByLabel('Código interno').fill('ANEXO-01');
    await createDialog.getByLabel('Nombre').fill('Almacén anexo');
    await createDialog.getByLabel('Dirección interna (opcional)').fill('Segundo ambiente');
    await createDialog.getByLabel('Establecimiento SUNAT del almacén').click();
    await page.getByRole('option', { name: /0000 · Establecimiento principal · 150101/ }).click();
    await createDialog.getByRole('button', { name: 'Crear almacén' }).click();

    await expect(page.getByText('Almacén creado.')).toBeVisible();
    const secondaryWarehouse = page.locator('.inventory-warehouse-card').filter({
      hasText: 'Almacén anexo',
    });
    await expect(secondaryWarehouse).toBeVisible();
    await expect(secondaryWarehouse.getByText('0000 · Ubigeo 150101')).toBeVisible();
    await expect(secondaryWarehouse.getByText('Datos SUNAT verificados')).toBeVisible();
    await expect(page.getByText('2 almacenes')).toBeVisible();
  });
});
