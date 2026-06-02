import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildCroppedImageFileName,
  getImagePointerPosition,
  constrainSquareCrop,
  getCropPercentStyle,
  getInitialSquareCrop,
  moveSquareCropByPointer,
  resizeSquareCropFromHandle,
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

test('getImagePointerPosition maps rendered image pixels to source pixels', () => {
  const point = getImagePointerPosition(
    { clientX: 150, clientY: 250 },
    { left: 50, top: 50, width: 200, height: 400 },
    { width: 400, height: 800 },
  );

  assert.deepEqual(point, { x: 200, y: 400 });
});

test('moveSquareCropByPointer drags the crop window inside the source image', () => {
  const crop = moveSquareCropByPointer(
    { x: 40, y: 50, size: 100 },
    { x: 60, y: 60 },
    { x: 95, y: 20 },
    { width: 240, height: 240 },
  );

  assert.deepEqual(crop, { x: 75, y: 10, size: 100 });
});

test('resizeSquareCropFromHandle resizes from a corner and preserves square bounds', () => {
  const crop = resizeSquareCropFromHandle(
    { x: 40, y: 50, size: 100 },
    'se',
    { x: 190, y: 200 },
    { width: 240, height: 240 },
    64,
  );

  assert.deepEqual(crop, { x: 40, y: 50, size: 150 });
});

test('resizeSquareCropFromHandle keeps opposite corner anchored when shrinking', () => {
  const crop = resizeSquareCropFromHandle(
    { x: 40, y: 50, size: 100 },
    'nw',
    { x: 100, y: 105 },
    { width: 240, height: 240 },
    64,
  );

  assert.deepEqual(crop, { x: 76, y: 86, size: 64 });
});
