import test from 'node:test';
import assert from 'node:assert/strict';
import { fiscalTrackingState } from './fiscalTracking.js';
import { buildFiscalListQuery } from './fiscalListQuery.js';
import { getFiscalDocumentStatus } from './documentArtifacts.js';

test('el seguimiento no confunde trabajo completado con aceptación', () => {
  assert.match(fiscalTrackingState({ status: 'succeeded' }).label, /Verificando/);
  assert.match(fiscalTrackingState({ status: 'succeeded' }, 'emitted').label, /Aceptado/);
  assert.match(fiscalTrackingState({ status: 'succeeded', action: 'void_fiscal_document' }, 'emitted').label, /Baja/);
  for (const status of ['queued', 'processing', 'retry', 'contingency_pending']) assert.equal(fiscalTrackingState({ status }).poll, true);
  for (const status of ['failed', 'pending_confirmation']) {
    assert.equal(fiscalTrackingState({ status }).poll, false);
    assert.equal(fiscalTrackingState({ status }).terminal, true);
  }
  assert.match(fiscalTrackingState({ status: 'failed' }).label, /no implica rechazo/);
});

test('paginación fiscal alcanza registros posteriores a 100 y conserva filtros', () => {
  const q = new URLSearchParams(buildFiscalListQuery({ page: 13, search: ' FA01-000180 ', filters: { tipo: '03', numero: '000180', serie: 'FA01', docReceptor: '20123456789', razonSocial: 'CLIENTE', formaPago: 'credito', desde: '2026-01-01', hasta: '2026-09-18', moneda: 'PEN' } }));
  assert.equal(q.get('skip'), '180'); assert.equal(q.get('limit'), '15');
  assert.equal(q.get('q'), 'FA01-000180'); assert.equal(q.get('tipo_comprobante'), '03');
  assert.equal(q.get('documento_cliente'), '20123456789'); assert.equal(q.get('forma_pago'), 'credito');
  assert.equal(q.get('razon_social'), 'CLIENTE'); assert.equal(q.get('numero'), '000180');
  assert.equal(q.get('serie'), 'FA01'); assert.equal(q.get('moneda'), 'PEN');
  assert.equal(q.get('desde'), '2026-01-01'); assert.equal(q.get('hasta'), '2026-09-18');
});

test('presentación autoritativa impide que anulado figure rechazado o aceptado', () => {
  const doc = { document_kind: 'fiscal_document', fiscal_status: 'voided', sunat_error: 'Error anterior', sunat_cdr_url: 'old-cdr', estado: 'anulada' };
  assert.equal(getFiscalDocumentStatus(doc).label, 'ANULADO');
  assert.notEqual(getFiscalDocumentStatus({ ...doc, fiscal_status: 'pending_confirmation' }).kind, 'ok');
});
