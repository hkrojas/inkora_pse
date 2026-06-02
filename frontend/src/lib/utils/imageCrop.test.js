import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildCroppedImageFileName,
  constrainSquareCrop,
  getCropPercentStyle,
  getInitialSquareCrop,
} from './imageCrop.js';

test('getInitialSquareCrop starts centered and smaller than the full screenshot', () => {
  const crop = getInitialSquareCrop(222, 234);

  assert.deepEqual(crop, {
    x: 36,
    y: 42,
    size: 151,
  });
});

test('constrainSquareCrop keeps crop inside the image bounds', () => {
  const crop = constrainSquareCrop(
    { x: 200, y: -20, size: 300 },
    { width: 222, height: 234 },
  );

  assert.deepEqual(crop, {
    x: 0,
    y: 0,
    size: 222,
  });
});

test('getCropPercentStyle maps source pixels to overlay percentages', () => {
  const style = getCropPercentStyle(
    { x: 36, y: 42, size: 151 },
    { width: 222, height: 234 },
  );

  assert.deepEqual(style, {
    left: '16.2162%',
    top: '17.9487%',
    width: '68.0180%',
    height: '64.5299%',
  });
});

test('buildCroppedImageFileName normalizes uploaded file names to png', () => {
  assert.equal(
    buildCroppedImageFileName('qr yape Gerardo.jpg'),
    'qr-yape-gerardo-qr.png',
  );
});
