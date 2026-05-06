import test from 'node:test';
import assert from 'node:assert/strict';
import { buildQueryString, getPageCount } from './queryParams.js';

test('buildQueryString omits empty values and keeps pagination filters stable', () => {
  assert.equal(
    buildQueryString({
      skip: 25,
      limit: 25,
      q: 'PAPELERIA',
      gre_status: '',
      active_status: null,
      tab: 'smartpse',
    }),
    '?skip=25&limit=25&q=PAPELERIA&tab=smartpse',
  );
});

test('getPageCount keeps empty result sets on page one', () => {
  assert.equal(getPageCount(0, 25), 1);
  assert.equal(getPageCount(1, 25), 1);
  assert.equal(getPageCount(1000, 25), 40);
});
