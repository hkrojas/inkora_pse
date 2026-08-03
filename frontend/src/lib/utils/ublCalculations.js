import Decimal from 'decimal.js';

Decimal.set({ precision: 40, rounding: Decimal.ROUND_HALF_UP });

const IGV_FACTOR = new Decimal('1.18');
const QUANTITY_DECIMALS = 4;
const UNIT_PRICE_DECIMALS = 4;
const VALUE_UNIT_DECIMALS = 10;
const MONEY_DECIMALS = 2;

function decimal(value) {
  if (value === null || value === undefined || value === '') return new Decimal(0);
  try {
    return new Decimal(String(value));
  } catch {
    return new Decimal(0);
  }
}

function fixed(value, places) {
  return decimal(value).toDecimalPlaces(places, Decimal.ROUND_HALF_UP).toFixed(places);
}

function taxed(item) {
  return String(item?.tipo_afectacion_igv || '10') === '10';
}

export function isPositiveDecimal(value) {
  return decimal(value).greaterThan(0);
}

export function normalizeQuantity(value) {
  return fixed(value, QUANTITY_DECIMALS);
}

export function normalizeUnitPrice(value) {
  return fixed(value, UNIT_PRICE_DECIMALS);
}

export function money(value) {
  return fixed(value, MONEY_DECIMALS);
}

export function sumMoney(values) {
  return decimal(values.reduce((total, value) => total.plus(decimal(value)), new Decimal(0))).toDecimalPlaces(
    MONEY_DECIMALS,
    Decimal.ROUND_HALF_UP,
  ).toFixed(MONEY_DECIMALS);
}

export function moneyDifference(left, right) {
  return decimal(left).minus(decimal(right)).toDecimalPlaces(MONEY_DECIMALS, Decimal.ROUND_HALF_UP).toFixed(MONEY_DECIMALS);
}

export function isSameMoney(left, right) {
  return decimal(money(left)).equals(decimal(money(right)));
}

export function priceWithIgv(item, incluyeIgv) {
  const entered = decimal(normalizeUnitPrice(item?.precio_unitario));
  if (taxed(item) && !incluyeIgv) {
    return entered.times(IGV_FACTOR).toDecimalPlaces(UNIT_PRICE_DECIMALS, Decimal.ROUND_HALF_UP).toFixed(UNIT_PRICE_DECIMALS);
  }
  return entered.toFixed(UNIT_PRICE_DECIMALS);
}

export function computeUblLine(item, incluyeIgv = true) {
  const quantity = decimal(normalizeQuantity(item?.cantidad));
  const unitFinal = decimal(priceWithIgv(item, incluyeIgv));
  const isGravado = taxed(item);
  const unitBasePrecise = isGravado ? unitFinal.div(IGV_FACTOR) : unitFinal;
  const subtotal = unitBasePrecise.times(quantity).toDecimalPlaces(MONEY_DECIMALS, Decimal.ROUND_HALF_UP);
  const total = unitFinal.times(quantity).toDecimalPlaces(MONEY_DECIMALS, Decimal.ROUND_HALF_UP);
  const igv = isGravado ? total.minus(subtotal) : new Decimal(0);

  return {
    cantidad: quantity.toFixed(QUANTITY_DECIMALS),
    precioIngresado: normalizeUnitPrice(item?.precio_unitario),
    unitBase: unitBasePrecise.toDecimalPlaces(VALUE_UNIT_DECIMALS, Decimal.ROUND_HALF_UP).toFixed(VALUE_UNIT_DECIMALS),
    unitFinal: unitFinal.toFixed(UNIT_PRICE_DECIMALS),
    subtotal: subtotal.toFixed(MONEY_DECIMALS),
    igv: igv.toFixed(MONEY_DECIMALS),
    total: total.toFixed(MONEY_DECIMALS),
  };
}

export function computeUblDocumentTotals(items, incluyeIgv = true) {
  const lines = (items || []).map((item) => computeUblLine(item, incluyeIgv));
  return {
    subtotal: sumMoney(lines.map((line) => line.subtotal)),
    igv: sumMoney(lines.map((line) => line.igv)),
    total: sumMoney(lines.map((line) => line.total)),
  };
}
