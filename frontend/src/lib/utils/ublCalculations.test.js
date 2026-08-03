import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { computeUblDocumentTotals, computeUblLine, priceWithIgv } from './ublCalculations.js';

const contract = JSON.parse(readFileSync(new URL('../../../../contracts/ubl21_calculation_cases.json', import.meta.url), 'utf8'));
const LINE_KEYS = ['cantidad', 'precio_unitario', 'valor_unitario', 'total_base_igv', 'total_igv', 'total_item'];

test('frontend decimal calculations match the shared UBL 2.1 contract', () => {
  for (const scenario of contract.cases) {
    const lines = scenario.items.map((item) => computeUblLine(item, true));
    for (const [index, expected] of scenario.expected.lines.entries()) {
      const actual = lines[index];
      const mapping = {
        cantidad: actual.cantidad,
        precio_unitario: actual.unitFinal,
        valor_unitario: actual.unitBase,
        total_base_igv: actual.subtotal,
        total_igv: actual.igv,
        total_item: actual.total,
      };
      for (const key of LINE_KEYS) assert.equal(mapping[key], expected[key], `${scenario.name}: ${key}`);
    }
    const subtotal = scenario.expected.lines
      .reduce((total, line) => total + Number(line.total_base_igv), 0)
      .toFixed(2);
    assert.deepEqual(computeUblDocumentTotals(scenario.items, true), {
      subtotal,
      igv: scenario.expected.totals.total_igv,
      total: scenario.expected.totals.total_venta,
    }, scenario.name);
  }
});

test('base-price input is converted to a four-decimal price including IGV before submission', () => {
  const item = { cantidad: '3', precio_unitario: '10', tipo_afectacion_igv: '10' };
  assert.equal(priceWithIgv(item, false), '11.8000');
  assert.deepEqual(computeUblDocumentTotals([item], false), { subtotal: '30.00', igv: '5.40', total: '35.40' });
});
