// Shared helpers for document emission module

import {
  SUNAT_TAX_AFFECTATION_OPTIONS,
  SUNAT_UNIT_OPTIONS,
} from './sunatCatalogs';
import {
  computeUblDocumentTotals,
  computeUblLine,
} from './ublCalculations';

export const IGV_FACTOR = 1.18;

export const PAYMENT_OPTIONS = [
  { value: 'contado',    label: 'Contado' },
  { value: 'credito_7',  label: 'Crédito 7 días' },
  { value: 'credito_15', label: 'Crédito 15 días' },
  { value: 'credito_30', label: 'Crédito 30 días' },
  { value: 'credito_60', label: 'Crédito 60 días' },
];

export const MEDIO_PAGO_OPTIONS = [
  { value: 'Efectivo',      label: 'Efectivo' },
  { value: 'Transferencia', label: 'Transferencia' },
  { value: 'Yape',          label: 'Yape' },
  { value: 'Plin',          label: 'Plin' },
  { value: 'Tarjeta',       label: 'Tarjeta' },
  { value: 'Deposito',      label: 'Depósito' },
];

export const OPERATION_OPTIONS = [
  { value: '0101', label: 'Venta interna' },
];

export const UNIT_OPTIONS = SUNAT_UNIT_OPTIONS;

export const AFECTACION_IGV_OPTIONS = SUNAT_TAX_AFFECTATION_OPTIONS;

export const MOTIVOS_NC = [
  { value: '01', label: '01 – Anulación de la operación' },
  { value: '02', label: '02 – Anulación por error en el RUC' },
  { value: '03', label: '03 – Corrección en la descripción' },
  { value: '04', label: '04 – Descuento global' },
  { value: '05', label: '05 – Descuento por ítem' },
  { value: '06', label: '06 – Devolución total' },
  { value: '07', label: '07 – Devolución por ítem' },
  { value: '08', label: '08 – Bonificación' },
  { value: '09', label: '09 – Disminución en el valor' },
  { value: '13', label: '13 – Ajustes de operaciones de exportación' },
];

export const MOTIVOS_ND = [
  { value: '01', label: '01 – Intereses por mora' },
  { value: '02', label: '02 – Aumento en el valor' },
  { value: '03', label: '03 – Penalidades / otros conceptos' },
];

export function inputDateToday() {
  const now = new Date();
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('-');
}

export function addDays(dateString, days) {
  if (!dateString || !days) return '';
  const [y, m, d] = dateString.split('-').map(Number);
  const base = new Date(y, m - 1, d);
  base.setDate(base.getDate() + days);
  return [
    base.getFullYear(),
    String(base.getMonth() + 1).padStart(2, '0'),
    String(base.getDate()).padStart(2, '0'),
  ].join('-');
}

export function paymentDays(condicion) {
  return { credito_7: 7, credito_15: 15, credito_30: 30, credito_60: 60 }[condicion] || 0;
}

export function toApiDate(dateString) {
  if (!dateString) return null;
  return `${dateString}T00:00:00-05:00`;
}

export function formatCurrency(value, moneda = 'PEN') {
  const symbol = moneda === 'USD' ? '$' : 'S/';
  const amount = Number(value || 0).toLocaleString('es-PE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${symbol} ${amount}`;
}

export function fmt(value) {
  return Number(value || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 });
}

export function deriveSeries(tipoComprobante, modoEmision, tenant = null) {
  if (modoEmision === 'contingencia') return '0001';
  const configured = tipoComprobante === '01'
    ? tenant?.fiscal_invoice_series
    : tenant?.fiscal_boleta_series;
  if (tenant?.smartpse_environment === 'produccion' && !configured) return 'SERIE';
  return String(configured || (tipoComprobante === '01' ? 'F001' : 'B001')).toUpperCase();
}

export function computeLine(item, incluyeIgv) {
  return computeUblLine(item, incluyeIgv);
}

export function computeDocumentTotals(items, incluyeIgv) {
  return computeUblDocumentTotals(items, incluyeIgv);
}

export function getSunatStatus(item) {
  if (item.estado === 'anulada')           return { label: 'ANULADO',   variant: 'danger',  kind: 'voided' };
  if (item.sunat_error)                    return { label: 'RECHAZADO', variant: 'danger',  kind: 'error', tooltip: item.sunat_error };
  if (item.sunat_accepted || item.sunat_xml_url) return { label: 'ACEPTADO',  variant: 'success', kind: 'ok' };
  if (item.document_kind !== 'quotation')  return { label: 'PENDIENTE', variant: 'warning', kind: 'pending' };
  return null;
}

export function validateRuc(doc) {
  if (!doc || doc.length !== 11 || !/^\d{11}$/.test(doc)) return false;
  const factors = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  const sum = factors.reduce((acc, f, i) => acc + f * Number(doc[i]), 0);
  const remainder = 11 - (sum % 11);
  const check = remainder >= 10 ? remainder - 10 : remainder;
  return check === Number(doc[10]);
}

export function getDocTypeLabel(tipo) {
  return { '01': 'Factura', '03': 'Boleta', '07': 'Nota Crédito', '08': 'Nota Débito', '00': 'Cotización' }[tipo] || tipo;
}
