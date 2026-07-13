import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildFiscalDownloadRequest,
  canRetryFiscalArtifacts,
  formatFiscalDate,
  getFiscalArtifactStatus,
  getFiscalDocumentStatus,
  hasFiscalDownload,
} from './documentArtifacts.js';

test('formatFiscalDate keeps fiscal day from ISO string without timezone drift', () => {
  assert.equal(formatFiscalDate('2026-06-19T00:00:00-05:00'), '19/06/2026');
  assert.equal(formatFiscalDate('2026-06-19'), '19/06/2026');
});

test('buildFiscalDownloadRequest uses internal PDF endpoint for fiscal documents', () => {
  assert.deepEqual(buildFiscalDownloadRequest({ id: 42 }, 'pdf'), {
    method: 'getBlob',
    path: '/cotizaciones/42/pdf/download',
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

test('getFiscalDocumentStatus accepts fiscal document with verified provider and CDR evidence', () => {
  const status = getFiscalDocumentStatus({
    document_kind: 'fiscal_document',
    estado: 'facturada',
    provider_verification_status: 'verified',
    sunat_cdr_url: 'private://cdr.zip',
  });

  assert.equal(status.kind, 'ok');
  assert.equal(status.label, 'ACEPTADO');
});

test('getFiscalDocumentStatus does not accept fiscal document when provider verification failed', () => {
  const status = getFiscalDocumentStatus({
    document_kind: 'fiscal_document',
    estado: 'facturada',
    provider_verification_status: 'failed',
    sunat_cdr_url: 'private://cdr.zip',
  });

  assert.equal(status.kind, 'error');
  assert.equal(status.label, 'RECHAZADO');
});

test('getFiscalDocumentStatus keeps provider verification pending separate from accepted CDR', () => {
  const status = getFiscalDocumentStatus({
    document_kind: 'fiscal_document',
    estado: 'facturada',
    provider_verification_status: 'pending',
    sunat_cdr_url: 'private://cdr.zip',
  });

  assert.equal(status.kind, 'pending');
  assert.equal(status.label, 'PENDIENTE');
});

test('hasFiscalDownload uses backend flags for XML and CDR buttons', () => {
  const doc = {
    id: 42,
    has_sunat_xml: true,
    has_sunat_cdr: true,
    sunat_xml_url: null,
    sunat_cdr_url: null,
  };

  assert.equal(hasFiscalDownload(doc, 'pdf'), true);
  assert.equal(hasFiscalDownload(doc, 'xml'), true);
  assert.equal(hasFiscalDownload(doc, 'cdr'), true);
});

test('hasFiscalDownload blocks missing failed PDF but allows CDR DB fallback', () => {
  assert.equal(hasFiscalDownload({ estado: 'facturada', pdf_artifact_status: 'failed' }, 'pdf'), false);
  assert.equal(
    hasFiscalDownload({ estado: 'facturada', cdr_artifact_status: 'failed', has_sunat_cdr: true }, 'cdr'),
    true,
  );
});

test('artifact status and retry helpers expose failed artifact state', () => {
  const doc = {
    id: 42,
    estado: 'facturada',
    provider_verification_status: 'verified',
    has_sunat_cdr: true,
    pdf_artifact_status: 'failed',
  };

  assert.deepEqual(getFiscalArtifactStatus(doc, 'pdf'), {
    label: 'PDF falló',
    variant: 'error',
    kind: 'failed',
  });
  assert.equal(canRetryFiscalArtifacts(doc), true);
});
