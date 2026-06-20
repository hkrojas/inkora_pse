import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildFiscalDownloadRequest,
  formatFiscalDate,
  getFiscalDocumentStatus,
} from './documentArtifacts.js';

test('formatFiscalDate keeps fiscal day from ISO string without timezone drift', () => {
  assert.equal(formatFiscalDate('2026-06-19T00:00:00-05:00'), '19/06/2026');
  assert.equal(formatFiscalDate('2026-06-19'), '19/06/2026');
});

test('buildFiscalDownloadRequest uses internal PDF endpoint for fiscal documents', () => {
  assert.deepEqual(buildFiscalDownloadRequest({ id: 42 }, 'pdf'), {
    method: 'get',
    path: '/cotizaciones/42/pdf',
  });
});

test('buildFiscalDownloadRequest keeps XML and CDR on fiscal artifact endpoint', () => {
  assert.deepEqual(buildFiscalDownloadRequest({ id: 42 }, 'xml'), {
    method: 'blob',
    path: '/facturacion/xml',
    body: { comprobante_id: 42 },
  });
}
);

test('getFiscalDocumentStatus does not accept XML without CDR', () => {
  const status = getFiscalDocumentStatus({
    document_kind: 'fiscal_document',
    estado: 'facturada',
    sunat_xml_url: 'https://storage.test/invoice.xml',
  });

  assert.equal(status.kind, 'pending');
  assert.equal(status.label, 'PENDIENTE');
});

test('getFiscalDocumentStatus accepts fiscal document with CDR evidence', () => {
  const status = getFiscalDocumentStatus({
    document_kind: 'fiscal_document',
    estado: 'facturada',
    sunat_cdr_url: 'private://cdr.zip',
  });

  assert.equal(status.kind, 'ok');
  assert.equal(status.label, 'ACEPTADO');
});
