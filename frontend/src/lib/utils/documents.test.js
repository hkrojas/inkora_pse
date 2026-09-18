import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildFiscalDownloadRequest,
  formatFiscalDate,
  getFiscalDocumentStatus,
  hasFiscalDownload,
} from './documentArtifacts.js';
import { deriveSeries } from './documents.js';


test('deriveSeries uses the fiscal series configured for the tenant', () => {
  const tenant = {
    smartpse_environment: 'produccion',
    fiscal_invoice_series: 'FA01',
    fiscal_boleta_series: 'BB01',
  };

  assert.equal(deriveSeries('01', 'cpe', tenant), 'FA01');
  assert.equal(deriveSeries('03', 'cpe', tenant), 'BB01');
});

test('deriveSeries does not invent a production series when configuration is missing', () => {
  assert.equal(
    deriveSeries('01', 'cpe', { smartpse_environment: 'produccion' }),
    'SERIE',
  );
});

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
    provider_verification_status: 'verified',
  });

  assert.equal(status.kind, 'ok');
  assert.equal(status.label, 'ACEPTADO');
});

test('getFiscalDocumentStatus does not accept unverified Smart PSE document', () => {
  const status = getFiscalDocumentStatus({
    document_kind: 'fiscal_document',
    estado: 'facturada',
    has_sunat_cdr: true,
    provider_verification_status: 'failed',
    provider_verification_error: 'Smart PSE remote verification missing',
  });

  assert.equal(status.kind, 'pending');
  assert.equal(status.label, 'NO VERIFICADO');
  assert.equal(status.tooltip, 'Smart PSE remote verification missing');
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

test('hasFiscalDownload blocks XML and CDR for unverified Smart PSE documents', () => {
  const doc = {
    id: 42,
    has_sunat_xml: true,
    has_sunat_cdr: true,
    provider_verification_status: 'failed',
  };

  assert.equal(hasFiscalDownload(doc, 'pdf'), true);
  assert.equal(hasFiscalDownload(doc, 'xml'), false);
  assert.equal(hasFiscalDownload(doc, 'cdr'), false);
});
