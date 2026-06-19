import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const ADVANCED_FISCAL_ROUTES = [
  '/resumen-diario',
  '/bajas',
  '/reversiones',
  '/retenciones',
  '/percepciones',
];

const TENANT_FACING_COPY_FILES = [
  '../../pages/ClientesPage.jsx',
  '../../pages/ConfiguracionPage.jsx',
  '../../pages/PercepcionesPage.jsx',
  '../../pages/ResumenDiarioPage.jsx',
  '../../pages/RetencionesPage.jsx',
  '../../pages/ReversionesPage.jsx',
];

function readSource(relativePath) {
  return readFileSync(new URL(relativePath, import.meta.url), 'utf8');
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

test('beta launch sidebar does not expose advanced fiscal routes by default', () => {
  const sidebarSource = readSource('../../components/Sidebar.jsx');

  for (const route of ADVANCED_FISCAL_ROUTES) {
    assert.doesNotMatch(
      sidebarSource,
      new RegExp(`to:\\s*['"]${escapeRegExp(route)}['"]`),
      `${route} should be hidden from the default beta sidebar`,
    );
  }
});

test('advanced fiscal direct routes are guarded by the beta fiscal gate', () => {
  const appSource = readSource('../../App.jsx');

  for (const route of ADVANCED_FISCAL_ROUTES) {
    assert.match(
      appSource,
      new RegExp(`path=['"]${escapeRegExp(route)}['"][\\s\\S]*<AdvancedFiscalRoute>`),
      `${route} should render through AdvancedFiscalRoute`,
    );
  }
});

test('tenant-facing beta copy does not name APISPeru as the visible provider', () => {
  for (const filePath of TENANT_FACING_COPY_FILES) {
    const source = readSource(filePath);
    assert.doesNotMatch(source, /APISPeru|ApisPeru/i, `${filePath} still mentions APISPeru`);
  }
});

test('settings exposes the PDF color designer entry point', () => {
  const settingsSource = readSource('../../pages/ConfiguracionPage.jsx');

  assert.match(settingsSource, /Colores de documentos PDF/);
  assert.match(settingsSource, /to=['"]\/diseno-pdf['"]/);
  assert.match(settingsSource, /Editar colores PDF/);
});

test('pdf designer keeps a styled side preview layout', () => {
  const designerSource = readSource('../../pages/PdfDesignerPage.jsx');
  const stylesSource = readSource('../../styles/globals.css');

  assert.match(designerSource, /pdf-designer-preview-panel/);
  assert.match(designerSource, /pdf-designer-preview-tabs/);
  assert.match(stylesSource, /\.pdf-designer-grid\s*\{/);
  assert.match(stylesSource, /\.pdf-designer-preview-panel\s*\{/);
  assert.match(stylesSource, /\.pdf-designer-preview-stage\s*\{/);
});

test('quote client selector searches tenant clients live by document or name', () => {
  const comboboxSource = readSource('../../components/ui/ClientCombobox.jsx');

  assert.match(comboboxSource, /cliSvc\.search\(query,\s*SEARCH_LIMIT/);
  assert.match(comboboxSource, /AbortController/);
  assert.match(comboboxSource, /clientMatchesQuery/);
  assert.match(comboboxSource, /setSearchingClients\(true\)/);
  assert.doesNotMatch(
    comboboxSource,
    /matchedClients\(activeField,\s*activeQuery,\s*remoteClients\)/,
    'remote client search results should not be narrowed again by the active input field',
  );
});

test('quote product lines search tenant products live by code or name', () => {
  const productLineSource = readSource('../../components/ui/ProductLineCell.jsx');

  assert.match(productLineSource, /productosSvc\.search\(query,\s*SEARCH_LIMIT/);
  assert.match(productLineSource, /AbortController/);
  assert.match(productLineSource, /productMatchesQuery/);
  assert.match(productLineSource, /setSearchingProducts\(true\)/);
  assert.doesNotMatch(
    productLineSource,
    /matchedProducts\(activeInput,\s*activeQuery,\s*remoteProducts\)/,
    'remote product search results should not be narrowed again by the active input field',
  );
});

test('quote and invoice client edits require explicit catalog update', () => {
  const upsertSource = readSource('./upsert.js');
  const quoteSource = readSource('../../pages/CotizacionesPage.jsx');
  const comprobanteSource = readSource('../../pages/ComprobanteNuevoPage.jsx');
  const comboboxSource = readSource('../../components/ui/ClientCombobox.jsx');

  assert.match(upsertSource, /updateExisting\s*=\s*true/);
  assert.match(upsertSource, /isDirty\s*&&\s*!updateExisting/);
  assert.match(upsertSource, /return\s*\{\s*id:\s*Number\(id\),\s*client:\s*null,\s*updated:\s*false\s*\}/);
  assert.match(upsertSource, /clienteSnapshotFromForm/);
  assert.match(comboboxSource, /lastSyncedValueRef/);
  assert.match(comboboxSource, /locked && isDirty && lastSyncedValueRef\.current === String\(value\)/);
  assert.match(quoteSource, /Actualizar ficha del cliente/);
  assert.match(quoteSource, /updateExistingClient/);
  assert.match(quoteSource, /onClientePersisted/);
  assert.match(quoteSource, /persistedClient/);
  assert.match(quoteSource, /cliente_snapshot/);
  assert.match(comprobanteSource, /Actualizar ficha del cliente/);
  assert.match(comprobanteSource, /updateExistingClient/);
  assert.match(comprobanteSource, /mergeClienteIntoCatalog/);
  assert.match(comprobanteSource, /persistedClient/);
  assert.match(comprobanteSource, /cliente_snapshot/);
});

test('payment QR cropper supports direct drag and corner resize', () => {
  const cropperSource = readSource('../../components/settings/PaymentQrCropper.jsx');

  assert.match(cropperSource, /getImagePointerPosition/);
  assert.match(cropperSource, /moveSquareCropByPointer/);
  assert.match(cropperSource, /resizeSquareCropFromHandle/);
  assert.match(cropperSource, /onPointerDown/);
  assert.match(cropperSource, /settings-qr-crop-handle/);
});

test('payment QR cropper uses the page body overlay with drag crop and zoom controls', () => {
  const cropperSource = readSource('../../components/settings/PaymentQrCropper.jsx');
  const stylesSource = readSource('../../styles/globals.css');

  assert.match(cropperSource, /createPortal/);
  assert.match(cropperSource, /document\.body/);
  assert.match(cropperSource, /setZoom/);
  assert.match(cropperSource, /settings-qr-crop-zoom-control/);
  assert.match(stylesSource, /\.settings-qr-crop-toolbar\s*\{/);
  assert.doesNotMatch(cropperSource, /settings-qr-crop-controls/);
  assert.doesNotMatch(cropperSource, /Tamano del recorte|Posicion horizontal|Posicion vertical/);
});

test('payment QR cropper stays above app chrome and fits the viewport', () => {
  const stylesSource = readSource('../../styles/globals.css');

  assert.match(
    stylesSource,
    /\.settings-qr-crop-overlay\s*\{[\s\S]*z-index:\s*(?:[1-9]\d{3,}|1000)/,
    'cropper overlay must sit above the app topbar and sidebar',
  );
  assert.match(
    stylesSource,
    /\.settings-qr-crop-overlay\s*\{[\s\S]*overflow:\s*auto/,
    'cropper overlay should scroll if the viewport is short',
  );
  assert.match(
    stylesSource,
    /\.settings-qr-crop-panel\s*\{[\s\S]*100dvh/,
    'cropper panel should use the dynamic viewport height',
  );
});


test('quote and invoice product edits require explicit catalog opt-in', () => {
  const syncSource = readSource('./productCatalogSync.js');
  const upsertSource = readSource('./upsert.js');
  const quoteSource = readSource('../../pages/CotizacionesPage.jsx');
  const comprobanteSource = readSource('../../pages/ComprobanteNuevoPage.jsx');

  assert.match(syncSource, /shouldSyncCatalogProduct/);
  assert.match(syncSource, /_syncCatalogChanges/);
  assert.match(upsertSource, /shouldSyncCatalogProduct/);
  assert.match(quoteSource, /Actualizar catalogo:\s*Si/);
  assert.match(comprobanteSource, /Actualizar catalogo:\s*Si/);
  assert.doesNotMatch(quoteSource, /catalogo de productos\?/);
  assert.doesNotMatch(comprobanteSource, /catalogo de productos\?/);
});
