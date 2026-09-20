import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getDispatchReservationLabel,
  getDispatchStatusLabel,
  getGuideStatusMeta,
  getSmartPseGreStatusMeta,
} from './fiscalStatus.js';

test('getGuideStatusMeta marks Smart PSE GRE as pending but provider-specific', () => {
  const meta = getGuideStatusMeta({
    estado: 'pendiente_smartpse',
    sunat_hash: 'abc123',
    sunat_ticket: 'T001-000005',
  });

  assert.equal(meta.tabKey, 'pending');
  assert.equal(meta.label, 'Pendiente Smart PSE');
  assert.equal(meta.badgeVariant, 'warning');
  assert.equal(meta.provider, 'smartpse');
  assert.match(meta.helper, /CDR pendiente/i);
});

test('getGuideStatusMeta keeps accepted guides in emitted tab', () => {
  const meta = getGuideStatusMeta({ estado: 'emitida' });

  assert.equal(meta.tabKey, 'emitted');
  assert.equal(meta.label, 'Emitida');
  assert.equal(meta.badgeVariant, 'success');
});

test('getGuideStatusMeta distinguishes a cancelled draft from a pending fiscal guide', () => {
  const meta = getGuideStatusMeta({ estado: 'cancelled' });

  assert.equal(meta.tabKey, 'cancelled');
  assert.equal(meta.label, 'Borrador cancelado');
  assert.equal(meta.badgeVariant, 'cancelled');
  assert.match(meta.helper, /cantidades reservadas fueron liberadas/i);
});

test('dispatch reservation states use operator-facing Spanish labels', () => {
  assert.equal(getDispatchReservationLabel('active'), 'Activa');
  assert.equal(getDispatchReservationLabel('covered'), 'Cubierta por GRE');
  assert.equal(getDispatchReservationLabel('released'), 'Liberada');
  assert.equal(getDispatchReservationLabel('provisional'), 'Provisional');
  assert.equal(getDispatchReservationLabel(null), 'No aplica');
});

test('dispatch lifecycle states use operator-facing Spanish labels', () => {
  assert.equal(getDispatchStatusLabel('draft'), 'Borrador con reserva');
  assert.equal(getDispatchStatusLabel('guide_pending'), 'GRE pendiente de resultado');
  assert.equal(getDispatchStatusLabel('guide_accepted'), 'GRE aceptada');
  assert.equal(getDispatchStatusLabel('departed'), 'Salida confirmada');
  assert.equal(getDispatchStatusLabel('cancelled'), 'Borrador cancelado');
  assert.equal(getDispatchStatusLabel(undefined), 'Sin estado operativo');
});

test('getSmartPseGreStatusMeta hides missing secrets behind status text only', () => {
  const meta = getSmartPseGreStatusMeta({
    has_smartpse_gre_credentials: false,
    smartpse_gre_status: 'ok',
  });

  assert.equal(meta.label, 'Pendiente');
  assert.equal(meta.badgeVariant, 'default');
  assert.equal(meta.canCheck, false);
});

test('getSmartPseGreStatusMeta exposes validation state without secret values', () => {
  const meta = getSmartPseGreStatusMeta({
    has_smartpse_gre_credentials: true,
    smartpse_gre_status: 'invalid',
  });

  assert.equal(meta.label, 'Revisar');
  assert.equal(meta.badgeVariant, 'danger');
  assert.equal(meta.canCheck, true);
  assert.deepEqual(Object.keys(meta).sort(), [
    'badgeVariant',
    'canCheck',
    'description',
    'label',
    'tone',
  ]);
});
