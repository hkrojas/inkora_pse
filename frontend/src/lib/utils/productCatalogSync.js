import {
  normalizeInternalProductCode,
  normalizeSunatUnitCode,
} from './sunatCatalogs.js';
import { forceUppercaseText } from './uppercase.js';

function normalizeText(value) {
  return forceUppercaseText(String(value || '').trim());
}

function normalizePrice(value) {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount)) return '0.00';

  const formatted = amount.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
  return formatted.includes('.') ? formatted : `${formatted}.00`;
}

function normalizeSnapshot(snapshot = {}) {
  return {
    codigo: normalizeInternalProductCode(snapshot.codigo || ''),
    descripcion: normalizeText(snapshot.descripcion || ''),
    precio_unitario: normalizePrice(snapshot.precio_unitario),
    unidad_medida: normalizeSunatUnitCode(snapshot.unidad_medida || 'NIU'),
    tipo_afectacion_igv: String(snapshot.tipo_afectacion_igv || '10').trim(),
  };
}

export function buildCatalogSnapshotFromProduct(product, { priceIncludesIgv = true } = {}) {
  const price = priceIncludesIgv
    ? Number(product?.precio_unitario || 0)
    : Number(product?.valor_unitario || product?.precio_unitario || 0);

  return normalizeSnapshot({
    codigo: product?.codigo_interno || '',
    descripcion: product?.nombre || product?.descripcion || '',
    precio_unitario: price,
    unidad_medida: product?.unidad_medida || 'NIU',
    tipo_afectacion_igv: product?.tipo_afectacion_igv || '10',
  });
}

export function buildCatalogSnapshotFromLine(item = {}) {
  return normalizeSnapshot({
    codigo: item.codigo || '',
    descripcion: item.descripcion || '',
    precio_unitario: item.precio_unitario,
    unidad_medida: item.unidad_medida || 'NIU',
    tipo_afectacion_igv: item.tipo_afectacion_igv || '10',
  });
}

export function hasCatalogProductOverrides(item) {
  if (!item?.producto_id || item?._isNew || !item?._catalogSnapshot) {
    return false;
  }

  const current = buildCatalogSnapshotFromLine(item);
  const original = normalizeSnapshot(item._catalogSnapshot);

  return (
    current.codigo !== original.codigo
    || current.descripcion !== original.descripcion
    || current.precio_unitario !== original.precio_unitario
    || current.unidad_medida !== original.unidad_medida
    || current.tipo_afectacion_igv !== original.tipo_afectacion_igv
  );
}

export function getCatalogProductOverrides(items = []) {
  return items.filter((item) => hasCatalogProductOverrides(item));
}

export function shouldSyncCatalogProduct(item) {
  return hasCatalogProductOverrides(item) && Boolean(item?._syncCatalogChanges);
}

export function getCatalogProductsToSync(items = []) {
  return items.filter((item) => shouldSyncCatalogProduct(item));
}

export function buildProductCatalogPayloadFromLine(item, { priceIncludesIgv = true } = {}) {
  const snapshot = buildCatalogSnapshotFromLine(item);
  return {
    nombre: snapshot.descripcion || 'Producto sin nombre',
    descripcion: snapshot.descripcion,
    codigo_interno: snapshot.codigo || undefined,
    precio_unitario: Number(item?.precio_unitario) || 1,
    precio_incluye_igv: priceIncludesIgv,
    unidad_medida: snapshot.unidad_medida,
    tipo_afectacion_igv: snapshot.tipo_afectacion_igv,
  };
}
