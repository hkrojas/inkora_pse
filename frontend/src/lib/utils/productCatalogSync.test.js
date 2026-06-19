import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getCatalogProductsToSync,
  hasCatalogProductOverrides,
  shouldSyncCatalogProduct,
} from './productCatalogSync.js';

function buildCatalogItem(overrides = {}) {
  return {
    producto_id: '15',
    codigo: 'PROD-001',
    descripcion: 'BOLSA KRAFT',
    precio_unitario: '12.00',
    unidad_medida: 'NIU',
    tipo_afectacion_igv: '10',
    _isNew: false,
    _syncCatalogChanges: false,
    _catalogSnapshot: {
      codigo: 'PROD-001',
      descripcion: 'BOLSA KRAFT',
      precio_unitario: '10.00',
      unidad_medida: 'NIU',
      tipo_afectacion_igv: '10',
    },
    ...overrides,
  };
}

test('shouldSyncCatalogProduct exige cambios reales y opt-in explicito', () => {
  const overrideOnly = buildCatalogItem();
  const overrideAndOptIn = buildCatalogItem({ _syncCatalogChanges: true });
  const noOverrideButOptIn = buildCatalogItem({
    precio_unitario: '10.00',
    _syncCatalogChanges: true,
  });

  assert.equal(hasCatalogProductOverrides(overrideOnly), true);
  assert.equal(shouldSyncCatalogProduct(overrideOnly), false);
  assert.equal(shouldSyncCatalogProduct(overrideAndOptIn), true);
  assert.equal(hasCatalogProductOverrides(noOverrideButOptIn), false);
  assert.equal(shouldSyncCatalogProduct(noOverrideButOptIn), false);
});

test('getCatalogProductsToSync devuelve solo productos existentes marcados para persistir', () => {
  const selected = buildCatalogItem({ producto_id: '21', _syncCatalogChanges: true });
  const localOnly = buildCatalogItem({ producto_id: '22', _syncCatalogChanges: false });
  const newProduct = {
    ...buildCatalogItem({
      producto_id: '',
      _isNew: true,
      _syncCatalogChanges: true,
      _catalogSnapshot: null,
    }),
  };

  const result = getCatalogProductsToSync([selected, localOnly, newProduct]);

  assert.deepEqual(result, [selected]);
});
