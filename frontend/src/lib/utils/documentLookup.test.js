import test from 'node:test';
import assert from 'node:assert/strict';
import { getLookupAddress } from './documentLookup.js';

test('getLookupAddress appends geographic fiscal fields with separators', () => {
  const address = getLookupAddress({
    direccion: 'AV. ALFONSO UGARTE NRO. 252 INT. 1023 BAR. MONSERRATE',
    departamento: 'LIMA',
    provincia: 'LIMA',
    distrito: 'LIMA',
  });

  assert.equal(
    address,
    'AV. ALFONSO UGARTE NRO. 252 INT. 1023 BAR. MONSERRATE - LIMA - LIMA - LIMA',
  );
});

test('getLookupAddress separates provider address suffix without duplicating it', () => {
  const address = getLookupAddress({
    direccion: 'AV. ALFONSO UGARTE NRO. 252 INT. 1023 BAR. MONSERRATE LIMA LIMA LIMA',
    departamento: 'LIMA',
    provincia: 'LIMA',
    distrito: 'LIMA',
  });

  assert.equal(
    address,
    'AV. ALFONSO UGARTE NRO. 252 INT. 1023 BAR. MONSERRATE - LIMA - LIMA - LIMA',
  );
});

test('getLookupAddress keeps raw address when geography is unavailable', () => {
  const address = getLookupAddress({
    direccion: 'JR. DEMO 123',
  });

  assert.equal(address, 'JR. DEMO 123');
});
