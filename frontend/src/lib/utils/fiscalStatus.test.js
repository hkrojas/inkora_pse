import test from 'node:test';
import assert from 'node:assert/strict';
import {
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

test('getSmartPseGreStatusMeta hides missing secrets behind status text only', () => {
  const meta = getSmartPseGreStatusMeta({
    has_smartpse_gre_credentials: false,
    smartpse_gre_status: 'ok',
  });

  assert.equal(meta.label, 'no configurado');
  assert.equal(meta.badgeVariant, 'default');
  assert.equal(meta.canCheck, false);
});

test('getSmartPseGreStatusMeta exposes validation state without secret values', () => {
  const meta = getSmartPseGreStatusMeta({
    has_smartpse_gre_credentials: true,
    smartpse_gre_status: 'invalid',
  });

  assert.equal(meta.label, 'inválido');
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
