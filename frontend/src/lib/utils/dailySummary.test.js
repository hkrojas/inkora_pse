import test from 'node:test';
import assert from 'node:assert/strict';
import { summaryStatus, summaryNumber, summaryResultMessage, uncertainSummarySend, SUMMARY_DETAIL_STATES } from './dailySummary.js';

test('a historical sent row does not establish acceptance until consulted', () => {
  const row = { status: 'sent', success: true, ticket: '123' };
  assert.equal(summaryStatus(row), 'unverified');
  assert.equal(summaryStatus(row, true), 'sent');
});

test('ticket, HTTP success, absent status and pending failure do not establish acceptance or rejection', () => {
  for (const row of [{}, { success: true, ticket: '123' }, { status: 'pending', success: false },
    { status: 'sent', success: false }, { status: 'unknown', success: true }, { sunatResponse: { success: false } }]) {
    assert.equal(summaryStatus(row, true), 'pending');
    assert.equal(summaryResultMessage(row).type, 'info');
  }
});

test('consulted acceptance and definitive rejection give distinct feedback', () => {
  assert.equal(summaryResultMessage({ status: 'sent', success: true }).type, 'success');
  const rejected = { status: 'rejected', success: false, sunat_error: 'SUNAT: documento rechazado' };
  assert.equal(summaryStatus(rejected), 'rejected');
  assert.deepEqual(summaryResultMessage(rejected), { message: rejected.sunat_error, type: 'error' });
  assert.match(summaryResultMessage({ status: 'pending', ticket: 'T-123' }).message, /Ticket: T-123/);
});

test('RC matches the shared backend summary date and padding, without duplicating normalized dates', () => {
  const dates = { fec_generacion: '2026-10-05T00:00:00-05:00', fec_resumen: '2026-10-04T00:00:00-05:00' };
  assert.equal(summaryNumber({ ...dates, correlativo: '1' }), 'RC-20261004-00001');
  assert.equal(summaryNumber({ ...dates, correlativo: '20261004-00002' }), 'RC-20261004-00002');
  assert.equal(summaryNumber({ ...dates, correlativo: 'RC-20261004-00002' }), 'RC-20261004-00002');
  assert.equal(summaryNumber({ ...dates, correlativo: '20261004-00002-1' }), 'RC-20261004-00002-1');
  assert.equal(summaryNumber({}), '-');
});

test('ambiguous send errors require consultation rather than a new submission', () => {
  for (const error of [{}, { isTimeout: true }, { status: null }, { status: 500 }, { status: 502 }]) {
    assert.equal(uncertainSummarySend(error), true);
  }
  for (const status of [400, 403, 404, 409, 422, 429]) assert.equal(uncertainSummarySend({ status }), false);
});

test('summary catalog19 keeps modification and annulment separate', () => {
  assert.deepEqual(SUMMARY_DETAIL_STATES.map(({ value, label }) => [value, label]), [
    ['1', '1 - Adicionar'], ['2', '2 - Modificar'], ['3', '3 - Anular'],
  ]);
});
