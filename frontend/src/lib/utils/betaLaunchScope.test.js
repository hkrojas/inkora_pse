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
