import assert from 'node:assert/strict';
import test from 'node:test';
import { inputDateToday } from './documents.js';
import { fiscalIssueDateError, fiscalIssueDateWindow } from './fiscalIssueDate.js';

test('new documents use the Lima date while the browser clock is on the next UTC day', () => {
  assert.equal(inputDateToday(new Date('2026-10-07T04:45:00Z')), '2026-10-06');
  assert.equal(inputDateToday(new Date('2026-10-07T05:00:00Z')), '2026-10-07');
});

test('individual invoice and receipt windows use Peru calendar dates', () => {
  const now = new Date('2026-10-07T04:45:00Z');
  assert.deepEqual(fiscalIssueDateWindow('01', now), { min: '2026-10-03', max: '2026-10-06', days: 3 });
  assert.deepEqual(fiscalIssueDateWindow('03', now), { min: '2026-10-01', max: '2026-10-06', days: 5 });
  for (const [type, boundary, expired] of [['01', '2026-10-03', '2026-10-02'], ['03', '2026-10-01', '2026-09-30']]) {
    assert.equal(fiscalIssueDateError(boundary, type, now), null);
    assert.match(fiscalIssueDateError(expired, type, now), /plazo/);
    assert.match(fiscalIssueDateError('2026-10-07', type, now), /futura/);
  }
  assert.match(fiscalIssueDateError('2026-02-30', '01', now), /válida/);
});

test('midnight expires the boundary without replacing the chosen date', () => {
  assert.equal(fiscalIssueDateError('2026-10-03', '01', new Date('2026-10-07T04:59:59Z')), null);
  assert.match(fiscalIssueDateError('2026-10-03', '01', new Date('2026-10-07T05:00:00Z')), /plazo/);
  assert.equal(fiscalIssueDateError('2026-10-06', '01', new Date('2026-10-07T05:00:00Z')), null);
});
