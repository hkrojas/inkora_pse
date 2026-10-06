import assert from 'node:assert/strict';
import test from 'node:test';
import { inputDateToday } from './documents.js';

test('new documents use the Lima date while the browser clock is on the next UTC day', () => {
  assert.equal(inputDateToday(new Date('2026-10-07T04:45:00Z')), '2026-10-06');
  assert.equal(inputDateToday(new Date('2026-10-07T05:00:00Z')), '2026-10-07');
});
