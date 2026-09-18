import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getEmissionJobLabel,
  getGuideEmissionJobCompletion,
  getGuideEmissionJobLabel,
  getEmissionOutcome,
  isEmissionJobActive,
} from './emissionJobs.js';

test('reports a deferred document without claiming SUNAT acceptance', () => {
  const outcome = getEmissionOutcome({
    deferred: true,
    job_status: 'contingency_pending',
  }, 'Factura');

  assert.equal(outcome.kind, 'deferred');
  assert.equal(outcome.shouldPoll, false);
  assert.equal(outcome.canShare, false);
  assert.match(outcome.message, /reservada en contingencia/i);
});

test('reports pending confirmation as a non-retryable warning', () => {
  const outcome = getEmissionOutcome({
    pending_confirmation: true,
    job_status: 'pending_confirmation',
  }, 'Boleta');

  assert.equal(outcome.kind, 'pending_confirmation');
  assert.equal(outcome.shouldPoll, false);
  assert.match(outcome.message, /evitar duplicados/i);
});

test('normal asynchronous emission remains pending until SUNAT accepts it', () => {
  const outcome = getEmissionOutcome({ job_status: 'queued' }, 'Factura');

  assert.equal(outcome.kind, 'processing');
  assert.equal(outcome.shouldPoll, true);
  assert.equal(outcome.canShare, false);
  assert.match(outcome.message, /aceptación de SUNAT aún está pendiente/i);
});

test('recognizes active statuses and provides operator-facing labels', () => {
  assert.equal(isEmissionJobActive('retry'), true);
  assert.equal(isEmissionJobActive('contingency_pending'), false);
  assert.equal(getEmissionJobLabel('pending_confirmation'), 'Pendiente de confirmación');
});

test('guide reconciliation copy never presents an inconclusive query as a failed emission', () => {
  const job = {
    action: 'consult_guide',
    status: 'pending_confirmation',
    last_error: 'Documento o ticket no encontrado',
  };

  assert.equal(getGuideEmissionJobLabel(job), 'Resultado pendiente de conciliación');
  assert.deepEqual(getGuideEmissionJobCompletion(job), {
    message: 'Smart PSE no devolvió un resultado definitivo. La guía no fue reenviada y conserva su reserva.',
    toastType: 'warning',
  });
});

test('guide reconciliation terminal UI copy distinguishes query from emission', () => {
  const job = {
    action: 'consult_guide',
    status: 'failed',
    last_error: 'Proveedor no disponible',
  };

  assert.equal(getGuideEmissionJobLabel(job), 'Consulta fiscal sin resultado');
  assert.deepEqual(getGuideEmissionJobCompletion(job), {
    message: 'Proveedor no disponible',
    toastType: 'error',
  });
});
