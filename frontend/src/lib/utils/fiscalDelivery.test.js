import test from 'node:test';
import assert from 'node:assert/strict';
import { fiscalDocumentId, isLinkedFiscalDocument } from './fiscalDelivery.js';

test('navigation uses the fiscal ID supplied by async or synchronous emission', () => {
  assert.equal(fiscalDocumentId({ resource_id: 42, source_quote_id: 7 }), 42);
  assert.equal(fiscalDocumentId({ document_id: 43, source_quote_id: 7 }), 43);
  for (const resource_id of [null, undefined, '', 0, -1, 1.5, true, 'invalid']) {
    assert.equal(fiscalDocumentId({ resource_id }), null);
  }
});

test('linked actions require the actual fiscal document and source relationship', () => {
  const quote = { id: 7, linked_fiscal_document_id: 42 };
  const doc = { id: 42, source_quote_id: 7, document_kind: 'fiscal_document', tipo_comprobante: '01' };
  assert.equal(isLinkedFiscalDocument(quote, doc), true);
  for (const patch of [{ id: 8 }, { source_quote_id: 9 }, { document_kind: 'quotation' }, { tipo_comprobante: '07' }]) {
    assert.equal(isLinkedFiscalDocument(quote, { ...doc, ...patch }), false);
  }
});
