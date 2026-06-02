const INITIAL_CROP_RATIO = 0.68;
const OUTPUT_SIZE = 720;

function toPositiveNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : 0;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function toPercent(value, total) {
  if (!total) return '0.0000%';
  return `${((value / total) * 100).toFixed(4)}%`;
}

export function getInitialSquareCrop(width, height) {
  const imageWidth = Math.round(toPositiveNumber(width));
  const imageHeight = Math.round(toPositiveNumber(height));
  const maxSize = Math.min(imageWidth, imageHeight);
  if (!maxSize) return { x: 0, y: 0, size: 0 };

  const size = Math.max(1, Math.round(maxSize * INITIAL_CROP_RATIO));
  return {
    x: Math.round((imageWidth - size) / 2),
    y: Math.round((imageHeight - size) / 2),
    size,
  };
}

export function constrainSquareCrop(crop, imageSize) {
  const width = Math.round(toPositiveNumber(imageSize?.width));
  const height = Math.round(toPositiveNumber(imageSize?.height));
  const maxSize = Math.min(width, height);
  if (!maxSize) return { x: 0, y: 0, size: 0 };

  const size = clamp(Math.round(toPositiveNumber(crop?.size) || maxSize), 1, maxSize);
  return {
    x: clamp(Math.round(Number(crop?.x) || 0), 0, Math.max(0, width - size)),
    y: clamp(Math.round(Number(crop?.y) || 0), 0, Math.max(0, height - size)),
    size,
  };
}

export function getCropPercentStyle(crop, imageSize) {
  const constrained = constrainSquareCrop(crop, imageSize);
  const width = toPositiveNumber(imageSize?.width);
  const height = toPositiveNumber(imageSize?.height);
  return {
    left: toPercent(constrained.x, width),
    top: toPercent(constrained.y, height),
    width: toPercent(constrained.size, width),
    height: toPercent(constrained.size, height),
  };
}

export function buildCroppedImageFileName(originalName = 'payment-qr') {
  const baseName = String(originalName || 'payment-qr')
    .replace(/\.[^.]+$/, '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    || 'payment-qr';
  return `${baseName}-qr.png`;
}

export function cropImageElementToPngFile(imageElement, crop, originalName = 'payment-qr') {
  const width = imageElement?.naturalWidth || 0;
  const height = imageElement?.naturalHeight || 0;
  const constrained = constrainSquareCrop(crop, { width, height });
  if (!width || !height || !constrained.size) {
    return Promise.reject(new Error('La imagen del QR no se pudo leer correctamente.'));
  }

  const canvas = document.createElement('canvas');
  canvas.width = OUTPUT_SIZE;
  canvas.height = OUTPUT_SIZE;
  const context = canvas.getContext('2d');
  if (!context) {
    return Promise.reject(new Error('El navegador no permite preparar el recorte del QR.'));
  }

  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);
  context.drawImage(
    imageElement,
    constrained.x,
    constrained.y,
    constrained.size,
    constrained.size,
    0,
    0,
    OUTPUT_SIZE,
    OUTPUT_SIZE,
  );

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('No se pudo generar el archivo recortado del QR.'));
        return;
      }
      resolve(new File([blob], buildCroppedImageFileName(originalName), { type: 'image/png' }));
    }, 'image/png');
  });
}
